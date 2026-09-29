import pytest
import datetime

import src.linkki_bot as main

def test_end_of_month():
    input = datetime.datetime(2026, 9, 29, 16, 0, 55, 880885)

    result = main.end_of_month(input)

    expected = datetime.datetime(2026, 9, 30, 23, 59, 59, 999999)
    assert result == expected

def test_end_of_week():
    input = datetime.datetime(2026, 9, 29, 16, 0, 55, 880885)

    result = main.end_of_week(input)

    expected = datetime.datetime(2026, 10, 4, 23, 59, 59, 999999)
    assert result == expected