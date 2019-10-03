import csv
import io
import warnings
from enum import Enum

import aiofile
from aiofile import LineReader


class OnError(Enum):
    leroy_jenkins = 'go_for_it_anyway'
    skip_silently = 'skip_silently'
    skip_and_warn = 'skip_and_warn'
    exception = 'exception'


class AsyncReaderError(Exception):
    pass


class AsyncReader:
    def __init__(self, aio_file: aiofile.AIOFile, csv_reader,
                 on_empty_line: OnError = OnError.skip_and_warn,
                 on_wrong_length: OnError = OnError.skip_and_warn,
                 **kwargs):
        self.on_empty_line = on_empty_line
        self.on_wrong_length = on_wrong_length
        self.line_sep = kwargs.pop('line_sep', '\n')
        self.file_reader = LineReader(
            aio_file, line_sep=self.line_sep,
            chunk_size=kwargs.pop('chunk_size', 4096),
            offset=kwargs.pop('offset', 0))
        self.buffer = io.BytesIO()
        self.csv_reader = csv_reader(
            io.TextIOWrapper(
                self.buffer,
                encoding=kwargs.pop('encoding', 'utf-8'),
                errors=kwargs.pop('errors', 'replace'),
            ), **kwargs)
        self.line_num = 0
        self.expected_num_fields = -1

    async def readline(self):
        self.line_num += 1
        line = await self.file_reader.readline()
        while line == self.line_sep and \
                self.on_empty_line is not OnError.leroy_jenkins:
            if self.on_empty_line is OnError.exception:
                raise AsyncReaderError(f'Empty line at line {self.line_num}')
            elif self.on_empty_line is OnError.skip_and_warn:
                warnings.warn(f'Empty line at line {self.line_num}')
            self.line_num += 1
            print(f'ignoring line {self.line_num}: {repr(line)}')
            line = await self.file_reader.readline()
        return line

    def __aiter__(self):
        return self

    async def __anext__(self):
        result = await self._next_row_no_verify()
        if self.on_wrong_length is not OnError.leroy_jenkins:
            num_fields = len(result)
            if self.expected_num_fields == -1:
                self.expected_num_fields = num_fields
            else:
                while num_fields != self.expected_num_fields:
                    message = (f'Incorrect record length at line {self.line_num} '
                               f'(expected {self.expected_num_fields}, found '
                               f'{num_fields})')
                    if self.on_wrong_length is OnError.exception:
                        raise AsyncReaderError(message)
                    elif self.on_wrong_length is OnError.skip_and_warn:
                        warnings.warn(message)
                    result = await self._next_row_no_verify()
                    num_fields = len(result)
        return result

    async def _next_row_no_verify(self):
        line = await self.readline()
        if not line:
            raise StopAsyncIteration
        self.buffer.write(line)
        self.buffer.seek(0)
        try:
            result = next(self.csv_reader)
        except StopIteration as e:
            raise StopAsyncIteration from e
        self.buffer.seek(0)
        self.buffer.truncate(0)
        return result


class AsyncDictReader(AsyncReader):
    def __init__(self, aio_file: aiofile.AIOFile, **kwargs):
        super().__init__(aio_file, csv_reader=csv.DictReader, **kwargs)

    async def __anext__(self):
        if self.line_num == 0:
            header = await self.readline()
            self.buffer.write(header)
        return await super().__anext__()


class AsyncListReader(AsyncReader):
    def __init__(self, aio_file: aiofile.AIOFile, **kwargs):
        super().__init__(aio_file, csv_reader=csv.reader, **kwargs)
