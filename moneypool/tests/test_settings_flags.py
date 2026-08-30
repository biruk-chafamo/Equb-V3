"""Boolean environment flags.

DEBUG=0 in Heroku config left Django running in debug mode in production for
months, because every non-empty string is truthy.
"""

import pytest

from config.settings import env_flag


@pytest.mark.parametrize('raw', ['0', 'false', 'False', 'FALSE', 'no', 'off', ''])
def test_falsey_strings_are_false(monkeypatch, raw):
    monkeypatch.setenv('EQUB_TEST_FLAG', raw)

    assert env_flag('EQUB_TEST_FLAG') is False


@pytest.mark.parametrize('raw', ['1', 'true', 'True', 'TRUE', 'yes', 'on', ' 1 '])
def test_truthy_strings_are_true(monkeypatch, raw):
    monkeypatch.setenv('EQUB_TEST_FLAG', raw)

    assert env_flag('EQUB_TEST_FLAG') is True


def test_an_unset_flag_takes_the_default(monkeypatch):
    monkeypatch.delenv('EQUB_TEST_FLAG', raising=False)

    assert env_flag('EQUB_TEST_FLAG') is False
    assert env_flag('EQUB_TEST_FLAG', default=True) is True
