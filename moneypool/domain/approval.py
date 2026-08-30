"""Who has to say yes before an outsider joins an equb."""
from enum import Enum


class JoinApprovalPolicy(str, Enum):
    """How a join request is carried. Stored on the equb."""

    MAJORITY = 'majority'
    CREATOR_ONLY = 'creator_only'
    UNANIMOUS = 'unanimous'


def required_approvals(member_count: int, policy: JoinApprovalPolicy = JoinApprovalPolicy.MAJORITY):
    """Approving members needed to carry a join request, or None if members do not decide."""
    if policy == JoinApprovalPolicy.UNANIMOUS:
        return member_count
    if policy == JoinApprovalPolicy.MAJORITY:
        return member_count // 2 + 1
    return None


def is_carried(
    approvals: int,
    member_count: int,
    policy: JoinApprovalPolicy = JoinApprovalPolicy.MAJORITY,
) -> bool:
    required = required_approvals(member_count, policy)
    return required is not None and approvals >= required


def is_unreachable(
    approvals: int,
    rejections: int,
    member_count: int,
    policy: JoinApprovalPolicy = JoinApprovalPolicy.MAJORITY,
) -> bool:
    required = required_approvals(member_count, policy)
    if required is None:
        return False
    return member_count - rejections < required
