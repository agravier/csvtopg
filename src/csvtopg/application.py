import asyncio
import csv
import logging
import re
import time
import traceback
from asyncio import Future
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import aiofile
import asyncpg
from csvtopg.aiocsv import AsyncListReader
from csvtopg.configuration import Config

log = logging.getLogger(__name__)

MAX_QUEUE_SIZE = 1000
EOS = object()  # end of stream nonce
STATUS_STRING_PATTERN = re.compile(r'COPY\s+(?P<num_rows>\d+)\s*$')


class Ticker:
    """Object returns the number of seconds since the last tick, including sleep
    >>> tick = Ticker()
    >>> tick()
    0.0
    """

    class InternalTicker:
        pass

    def __init__(self):
        self.instance = None

    def __call__(self) -> float:
        t = time.perf_counter()
        if self.instance is None:
            t0 = t
            self.instance = self.InternalTicker()
        else:
            t0 = self.instance.time
        self.instance.time = t
        return self.instance.time - t0


class CSVToPgError(Exception):
    pass


@dataclass
class Metrics:
    wall_clock_computation_time: Optional[float] = None  # in seconds
    num_rows_read: int = 0
    num_rows_written: int = 0


@dataclass
class ExecutionResult:
    metrics: Metrics = field(default_factory=Metrics)
    errors: List = field(default_factory=list)


def parse_insert_status_string(status_string: str) -> int:
    match = re.match(STATUS_STRING_PATTERN, status_string)
    if match is not None:
        return int(match.group('num_rows'))
    log.debug('Unexpected INSERT response: %s', status_string)
    raise CSVToPgError(f'Unexpected INSERT response: "{status_string}"')


async def clear_queue(q: asyncio.Queue):
    q._queue.clear()
    q._finished.set()
    q._unfinished_tasks = 0
    await q.put(EOS)


class CSVToPg:
    def __init__(self, config: Config):
        self.config = config
        self.file_reader_task: Optional[Future] = None
        self.postgres_task: Optional[Future] = None
        self.tick = Ticker()
        self._header: Optional[List[str]] = None
        self._record_length: Optional[int] = None
        self._exception: Optional[BaseException] = None

    @property
    def header(self) -> List[str]:
        if self._header is None:
            with open(self.config.input_file, newline='') as csvfile:
                reader = csv.reader(csvfile)
                self._header = next(reader)
        return self._header

    @property
    def record_length(self) -> int:
        if self._record_length is None:
            self._record_length = len(self.header)
        return self._record_length

    @property
    def schema(self) -> str:
        return ',\n'.join((f'    "{col}" text' for col in self.header))

    async def read_file(self, q: asyncio.Queue) -> int:
        num_rows_read = 0
        try:
            async with aiofile.AIOFile(self.config.input_file, 'rb') as f:
                log.debug('[read_file] Reading %s', self.config.input_file)
                reader = AsyncListReader(f)
                await reader.__anext__()  # skip the header
                async for row in reader:
                    num_rows_read += 1
                    await q.put(row)
                    # if num_rows_read > 100:
                    #     raise Exception()
            log.debug('[read_file] Read %d rows', num_rows_read)
            await q.put(EOS)
        except KeyboardInterrupt:
            log.warning('[read_file] User interrupt')
            await clear_queue(q)
        except asyncio.CancelledError:
            log.warning('[read_file] Task cancelled')
        except Exception as e:  # noqa
            self._exception = e
            await clear_queue(q)
        return num_rows_read

    async def stream_to_postgres(self, q: asyncio.Queue):
        try:
            conn = await asyncpg.connect(self.config.conn_uri)
        except Exception as e:  # noqa
            self._exception = e
            self.file_reader_task.cancel()
            return 0
        log.debug('[stream_to_postgres] Connected to %s', self.config.conn_uri)
        num_rows_written = 0
        try:
            await conn.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.config.table_name} (
                    {self.schema})''')
            eos = False
            while not eos:
                records = deque([await q.get()])
                while not q.empty():
                    record = await q.get()
                    records.append(record)
                if records[-1] is EOS:
                    eos = True
                    records.pop()
                if records:
                    status = await conn.copy_records_to_table(
                        self.config.table_name, records=records)
                    num_rows_written += parse_insert_status_string(status)
                    q.task_done()
            log.debug('[stream_to_postgres] Wrote %d rows', num_rows_written)
        except KeyboardInterrupt:
            log.warning('[stream_to_postgres] User interrupt')
        except asyncio.CancelledError:
            log.warning('[stream_to_postgres] Task cancelled')
            raise
        except Exception as e:  # noqa
            log.error('[stream_to_postgres] Exception: %s', e)
            raise
        finally:
            await conn.close()
        print('[read_file] returning')
        return num_rows_written

    async def schedule_coroutines(self) -> Tuple[int, int]:
        q = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        self.file_reader_task = asyncio.ensure_future(self.read_file(q))
        self.postgres_task = asyncio.ensure_future(self.stream_to_postgres(q))
        return await asyncio.gather(self.file_reader_task, self.postgres_task)

    def run(self) -> ExecutionResult:
        self.tick()
        self._exception = None
        loop = asyncio.get_event_loop()
        result = ExecutionResult()
        num_rows_read = num_rows_written = 0
        try:
            num_rows_read, num_rows_written = \
                loop.run_until_complete(self.schedule_coroutines())
            if self._exception:
                e = self._exception
                details = '\n'.join(
                    traceback.format_exception(None, e, e.__traceback__))
                result.errors.append(
                    f'Uncaught exception: {repr(e)}, traceback: {details}')
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            result.metrics.num_rows_read = num_rows_read
            result.metrics.num_rows_written = num_rows_written
            result.metrics.wall_clock_computation_time = self.tick()
        return result
