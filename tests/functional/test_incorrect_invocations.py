from csvtopg.application import CSVToPg
from csvtopg.configuration import Config


def test_inexistent_database_and_inexistent_file():
    result = CSVToPg(Config("test", "table", "test", False, "INFO")).run()
    assert result.errors != []
