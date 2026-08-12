import pytest

from moneypool.domain.validation import (
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


def test_is_member():
    assert is_member(2, [1, 2, 3]) is True
    assert is_member(4, [1, 2, 3]) is False
    assert is_member(2, {1, 2, 3}) is True
    assert is_member(4, set()) is False


def test_is_max_members_too_low():
    assert is_max_members_too_low(1) is True
    assert is_max_members_too_low(2) is False
    assert is_max_members_too_low(3) is False


def test_is_max_members_too_high():
    assert is_max_members_too_high(21) is True
    assert is_max_members_too_high(20) is False
    assert is_max_members_too_high(2) is False


def test_is_self_request():
    assert is_self_request(1, 1) is True
    assert is_self_request(1, 2) is False


def test_is_accept_and_reject_conflict():
    assert is_accept_and_reject_conflict(True, True) is True
    assert is_accept_and_reject_conflict(True, False) is False
    assert is_accept_and_reject_conflict(False, True) is False
    assert is_accept_and_reject_conflict(None, None) is False


def test_is_final_round():
    assert is_final_round(current_round=2, max_members=2) is True
    assert is_final_round(current_round=2, max_members=3) is False
    assert is_final_round(current_round=3, max_members=3) is True
