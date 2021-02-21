from .models import SmartGroup, SmartFilter
from allianceauth.groupmanagement.models import GroupRequest
from allianceauth.groupmanagement.managers import GroupManager
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse, JsonResponse
import logging

from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.contrib.auth.models import Group
from django.db.models import Q
from django.conf import settings
from django.shortcuts import render, redirect
from collections import defaultdict
from django.http import Http404
from django.db.models import Count

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
def groups_manager_checks(request, sg_id=None, filter_id=None):
    logger.debug("groups_manager_checks called by user %s" % request.user)
    if request.method == "POST":
        sg = SmartGroup.objects.get(id=sg_id)
        fltr = SmartFilter.objects.get(id=filter_id)
        users = sg.group.user_set.all()
        out = []
        try:
            _o = fltr.filter_object.audit_filter(users)
        except Exception as e:
            print(e)
            _o = defaultdict(lambda: None)

        for u in users:
            check = None
            msg = ""
            try:
                check = _o[u.id]["check"]
                msg = _o[u.id]["message"]
            except Exception:
                pass
            out.append({"uid": u.id,
                        "fid": filter_id,
                        "result": check,
                        "message": msg})

        return JsonResponse(out, safe=False)
    raise Http404("Does not exist")


@permission_required("securegroups.access_sec_group")
def groups_manager_view(request, sg_id=None):
    logger.debug("groups_manager_view called by user %s" % request.user)

    sg = SmartGroup.objects.get(id=sg_id)
    users = sg.group.user_set.all()
    filters = []
    out = {}
    for u in users:
        out[u.id] = u.profile.main_character
    for fltr in sg.filters.all():
        filters.append(fltr)

    context = {"sg": sg,
               "filters": filters,
               "characters": out}

    return render(request, "smartgroups/audit.html", context=context)


@permission_required("securegroups.access_sec_group")
def groups_manager_list(request):
    logger.debug("groups_manager_list called by user %s" % request.user)

    # Get all open and closed groups
    if GroupManager.has_management_permission(request.user):
        # Full access
        groups = GroupManager.get_all_non_internal_groups()
    else:
        # Group leader specific
        groups = GroupManager.get_group_leaders_groups(request.user)

    groups_qs = groups.exclude(authgroup__internal=True)

    smart_groups_qs = SmartGroup.objects.filter(
        group__in=groups_qs, enabled=True
    ).select_related("group", "group__authgroup").annotate(num_members=Count('group__user')).order_by('group__name')

    context = {"sgs": smart_groups_qs}

    return render(request, "smartgroups/audit_list.html", context=context)


@permission_required("securegroups.access_sec_group")
def smart_group_run_check(request, group_id):
    try:
        smart_group = SmartGroup.objects.get(group__id=group_id)
        filters = smart_group.run_check_on_user(request.user)
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
