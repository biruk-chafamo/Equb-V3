from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from ..adapters.django_notifier import default_notifier
from ..domain import approval
from ..models import EqubJoinRequest, EqubJoinRequestVote
from ..ports.notifier import Notifier


def create_join_request(sender, equb, notifier: Notifier = default_notifier) -> EqubJoinRequest:
    join_request = EqubJoinRequest.objects.create(sender=sender, receiver=equb.creator, equb=equb)
    notifier.join_request_created(join_request)
    return join_request


def cast_vote(
    join_request, voter, approve: bool, notifier: Notifier = default_notifier
) -> EqubJoinRequestVote:
    equb = join_request.equb

    if join_request.is_accepted or join_request.is_rejected or join_request.is_expired:
        raise serializers.ValidationError({"request": "This join request has already been decided."})
    if equb.is_active or equb.is_completed:
        raise serializers.ValidationError({"equb": f"{equb.name} has already began."})
    if voter == join_request.sender:
        raise serializers.ValidationError({"voter": "You cannot vote on your own join request."})
    if not equb.members.filter(pk=voter.pk).exists():
        raise PermissionDenied(f"Only members of {equb.name} can vote on join requests.")

    vote, _ = EqubJoinRequestVote.objects.update_or_create(
        request=join_request, voter=voter, defaults={'approve': approve}
    )

    if voter == equb.creator:
        _settle(join_request, approve, notifier)
    else:
        _tally(join_request, notifier)
    return vote


def _tally(join_request, notifier: Notifier) -> None:
    equb = join_request.equb
    # a queryset, not the related manager: the caller's prefetch cache predates this vote
    votes = EqubJoinRequestVote.objects.filter(request=join_request)
    approvals = sum(1 for vote in votes if vote.approve)
    rejections = len(votes) - approvals
    member_count = equb.members.count()
    policy = equb.join_approval_policy

    if approval.is_carried(approvals, member_count, policy):
        _settle(join_request, True, notifier)
    elif approval.is_unreachable(approvals, rejections, member_count, policy):
        _settle(join_request, False, notifier)
    else:
        notifier.join_request_voted(join_request)


def _settle(join_request, accepted: bool, notifier: Notifier) -> None:
    join_request.is_accepted = accepted
    join_request.is_rejected = not accepted
    join_request.save()
    notifier.join_request_voted(join_request)
