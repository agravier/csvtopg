# -*- coding: utf-8 -*-

import pytest

from csvtopg.configuration import Config


def test_invalid_log_level_returns_an_error():
    assert Config(conn_uri="1",
                  table_name="table",
                  input_file="1",
                  use_uvloop=False,
                  log_level='INFU').configuration_issues != []
