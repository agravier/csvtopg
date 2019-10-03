from csvtopg.application import CSVToPg
from csvtopg.configuration import Config


def test_uvloop_is_faster():
    result_without_uvloop = CSVToPg(Config(
        "test", "table", "test", False, "INFO")).run()
    result_with_uvloop = CSVToPg(Config(
        "test", "table", "test", True, "INFO")).run()
    assert (result_with_uvloop.metrics.wall_clock_computation_time <
            result_without_uvloop.metrics.wall_clock_computation_time)
