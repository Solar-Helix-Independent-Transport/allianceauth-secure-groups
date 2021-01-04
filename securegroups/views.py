from .models import SmartGroup
from allianceauth.groupmanagement.models import GroupRequest
from allianceauth.groupmanagement.managers import GroupManager
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse
import logging

from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.contrib.auth.models import Group
from django.db.models import Q
from django.conf import settings
from django.shortcuts import render, redirect

from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@permission_required("securegroups.access_sec_group")
def groups_view(request):
    logger.debug("groups_view called by user %s" % request.user)

    groups_qs = Group.objects.filter(
        Q(authgroup__states=request.user.profile.state) | Q(authgroup__states=None)
    )

    smart_groups_qs = SmartGroup.objects.filter(
        group__in=groups_qs, auto_group=False, enabled=True
    ).select_related("group", "group__authgroup")

    groups = []
    for smart_group in smart_groups_qs:
        group_request = GroupRequest.objects.filter(user=request.user).filter(
            group=smart_group.group
        )
        groups.append(
            {
                "smart_group": smart_group,
                "request": group_request[0] if group_request else None,
            }
        )

    context = {"groups": groups}
    return render(request, "smartgroups/groups.html", context=context)


@permission_required("securegroups.access_sec_group")
def smart_group_run_check(request, group_id):
    try:
        smart_group = SmartGroup.objects.get(group__id=group_id)
        filters = smart_group.run_checks(request.user)
        pass_checks = smart_group.process_checks(filters)
        ctx = {"filters": filters,
               "pass_checks": pass_checks, "group_id": group_id}
    except Exception as e:
        logger.error("Smart Group Failed to process!", exc_info=1)
        ctx = {
            "message": "Running Group Check Failed, Please contact an Admin!\n{}".format(e)
        }

    return HttpResponse(render_to_string("smartgroups/user_check.html", ctx, request=request))


@permission_required("securegroups.access_sec_group")
def group_request_add(request, group_id):
    logger.debug(
        "group_request_add called by user %s for group id %s" % (
            request.user, group_id)
    )
    group = Group.objects.get(id=group_id)
    if group in request.user.groups.all():
        # User is already a member of this group.
        logger.warning(
            "User %s attempted to join group id %s but they are already a member."
            % (request.user, group_id)
        )
        messages.warning(request, _("You are already a member of that group."))
        return redirect("securegroups:groups")
    if group.authgroup.open:
        logger.info("%s joining %s as is an open group" %
                    (request.user, group))
        request.user.groups.add(group)
        return redirect("securegroups:groups")
    req = GroupRequest.objects.filter(user=request.user, group=group).count()
    if req > 0:
        logger.info(
            "%s attempted to join %s but already has an open application"
            % (request.user, group)
        )
        messages.warning(
            request, _("You already have a pending application for that group.")
        )
        return redirect("securegroups:groups")
    grouprequest = GroupRequest()
    grouprequest.status = _("Pending")
    grouprequest.group = group
    grouprequest.user = request.user
    grouprequest.leave_request = False
    grouprequest.save()
    logger.info(
        "Created group request for user %s to group %s"
        % (request.user, Group.objects.get(id=group_id))
    )
    messages.success(request, _("Applied to group %(group)s.") %
                     {"group": group})
    return redirect("securegroups:groups")


@permission_required("securegroups.access_sec_group")
def group_request_leave(request, group_id):
    logger.debug(
        "group_request_leave called by user %s for group id %s"
        % (request.user, group_id)
    )
    group = Group.objects.get(id=group_id)
    if not GroupManager.check_internal_group(group):
        logger.warning(
            "User %s attempted to leave group id %s but it is not a joinable group"
            % (request.user, group_id)
        )
        messages.warning(request, _("You cannot leave that group"))
        return redirect("securegroups:groups")
    if group not in request.user.groups.all():
        logger.debug(
            "User %s attempted to leave group id %s but they are not a member"
            % (request.user, group_id)
        )
        messages.warning(request, _("You are not a member of that group"))
        return redirect("securegroups:groups")
    if group.authgroup.open:
        logger.info("%s leaving %s as is an open group" %
                    (request.user, group))
        request.user.groups.remove(group)
        return redirect("securegroups:groups")
    req = GroupRequest.objects.filter(user=request.user, group=group).count()
    if req > 0:
        logger.info(
            "%s attempted to leave %s but already has an pending leave request."
            % (request.user, group)
        )
        messages.warning(
            request, _(
                "You already have a pending leave request for that group.")
        )
        return redirect("securegroups:groups")
    if getattr(settings, "AUTO_LEAVE", False):
        logger.info(
            "%s leaving joinable group %s due to auto_leave" % (
                request.user, group)
        )
        request.user.groups.remove(group)
        return redirect("securegroups:groups")
    grouprequest = GroupRequest()
    grouprequest.status = _("Pending")
    grouprequest.group = group
    grouprequest.user = request.user
    grouprequest.leave_request = True
    grouprequest.save()
    logger.info(
        "Created group leave request for user %s to group %s"
        % (request.user, Group.objects.get(id=group_id))
    )
    messages.success(request, _(
        "Applied to leave group %(group)s.") % {"group": group})
    return redirect("securegroups:groups")
