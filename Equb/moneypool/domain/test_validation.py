import pytest

from .validation import (
    is_accept_and_reject_conflict,
    is_blank_email,
    is_final_round,
    is_max_members_too_high,
    is_max_members_too_low,
    is_member,
    is_self_request,
    passwords_match,
)


def test_is_blank_email():
    assert is_blank_email('') is True
    assert is_blank_email(None) is True
    assert is_blank_email('a@example.com') is False


def test_passwords_match():
    assert passwords_match('a', 'a') is True
    assert passwords_match('a', 'b') is False


