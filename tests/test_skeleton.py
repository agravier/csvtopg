# -*- coding: utf-8 -*-

import pytest
from csvtopg.skeleton import fib

__author__ = "Alexandre Gravier"
__copyright__ = "Alexandre Gravier"
__license__ = "mit"


def test_fib():
    assert fib(1) == 1
    assert fib(2) == 1
    assert fib(7) == 13
    with pytest.raises(AssertionError):
        fib(-10)
