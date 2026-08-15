from hypothesis import given, strategies as st

from moneypool.domain.approval import (
    CREATOR_ONLY,
    MAJORITY,
    UNANIMOUS,
    is_carried,
    is_unreachable,
    required_approvals,
)

_sizes = st.integers(min_value=1, max_value=20)


class TestMajority:
    @given(_sizes)
    def test_a_majority_is_strictly_more_than_half(self, member_count):
        required = required_approvals(member_count, MAJORITY)
        assert required * 2 > member_count
        assert (required - 1) * 2 <= member_count

    @given(_sizes, st.data())
    def test_two_disjoint_groups_cannot_both_carry(self, member_count, data):
        here = data.draw(st.integers(min_value=0, max_value=member_count))
        there = data.draw(st.integers(min_value=0, max_value=member_count - here))
        assert not (
            is_carried(here, member_count, MAJORITY)
            and is_carried(there, member_count, MAJORITY)
        )

    @given(_sizes)
    def test_every_member_approving_always_carries(self, member_count):
        assert is_carried(member_count, member_count, MAJORITY)

    @given(_sizes, st.integers(min_value=0, max_value=20))
    def test_no_approval_count_is_both_carried_and_unreachable(self, member_count, approvals):
        approvals = min(approvals, member_count)
        rejections = member_count - approvals
        assert not (
            is_carried(approvals, member_count, MAJORITY)
            and is_unreachable(approvals, rejections, member_count, MAJORITY)
        )

    @given(_sizes)
    def test_everyone_rejecting_is_unreachable(self, member_count):
        assert is_unreachable(0, member_count, member_count, MAJORITY)


class TestUnanimous:
    @given(_sizes)
    def test_unanimous_needs_every_member(self, member_count):
        assert required_approvals(member_count, UNANIMOUS) == member_count
        assert not is_carried(member_count - 1, member_count, UNANIMOUS)
        assert is_carried(member_count, member_count, UNANIMOUS)

    @given(_sizes)
    def test_a_single_rejection_makes_unanimity_unreachable(self, member_count):
        assert is_unreachable(0, 1, member_count, UNANIMOUS)


class TestCreatorOnly:
    @given(_sizes, st.integers(min_value=0, max_value=20))
    def test_member_votes_never_decide(self, member_count, approvals):
        assert required_approvals(member_count, CREATOR_ONLY) is None
        assert not is_carried(approvals, member_count, CREATOR_ONLY)
        assert not is_unreachable(approvals, member_count, member_count, CREATOR_ONLY)
