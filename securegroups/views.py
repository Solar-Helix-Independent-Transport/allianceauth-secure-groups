from .models import GracePeriodRecord, SmartGroup, SmartFilter
from allianceauth.groupmanagement.models import GroupRequest, RequestLog
from allianceauth.groupmanagement.managers import GroupManager
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse, JsonResponse
import logging

from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.contrib.auth.models import Group
from django.db.models import Q
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from collections import defaultdict
from django.http import Http404
from django.db.models import Count
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

from django.template.loader import render_to_string

from .tasks import run_smart_group_update
logger = logging.getLogger(__name__)


@permission_required("securegroups.access_sec_group")
def groups_view(request):
    logger.debug("groups_view called by user %s" % request.user)
    usr_groups = request.user.groups.all()
    groups_qs = Group.objects.filter(
        Q(authgroup__states=request.user.profile.state) | Q(authgroup__states=None)
    )

    smart_groups_qs = SmartGroup.objects.filter(
        group__in=groups_qs, auto_group=False, enabled=True
    ).select_related("group", "group__authgroup")
    graces_qs = GracePeriodRecord.objects.filter(user=request.user)
    graces = {}
    for g in graces_qs:
        if g.group.group.name not in graces:
            graces[g.group.group.name] = []
        graces[g.group.group.name].append(
            g.grace_filter.filter_object.description)
    groups = []
    for smart_group in smart_groups_qs:
        group_request = GroupRequest.objects.filter(user=request.user).filter(
            group=smart_group.group
        )
        grace_msg = None
        if smart_group.group.name in graces and smart_group.group in usr_groups:
            grace_msg = "<br>".join(graces[smart_group.group.name])
        groups.append(
            {
                "smart_group": smart_group,
                "request": group_request[0] if group_request else None,
                "grace_msg": grace_msg
            }
        )

    context = {"groups": groups}
    return render(request, "smartgroups/groups.html", context=context)


@permission_required("securegroups.audit_sec_group")
@user_passes_test(GroupManager.can_manage_groups)
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


@permission_required("securegroups.audit_sec_group")
@user_passes_test(GroupManager.can_manage_groups)
def groups_manager_view(request, sg_id=None):
    logger.debug("groups_manager_view called by user %s" % request.user)

    sg = SmartGroup.objects.get(id=sg_id)
    users = sg.group.user_set.all()
    graces = []
    for gp in sg.graceperiodrecord_set.all():
        if gp.user.id not in graces:
            graces.append(gp.user.id)

    filters = []
    out = {}
    for u in users:
        out[u.id] = u.profile.main_character
    for fltr in sg.filters.all():
        filters.append(fltr)

    context = {"sg": sg,
               "filters": filters,
               "graces": graces,
               "characters": out}

    return render(request, "smartgroups/audit.html", context=context)


@permission_required("securegroups.audit_sec_group")
@user_passes_test(GroupManager.can_manage_groups)
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
    ).select_related("group", "group__authgroup").annotate(num_members=Count('group__user', distinct=True),
                                                           pending_rem=Count('graceperiodrecord__user', distinct=True)).order_by('group__name')

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


@permission_required("securegroups.audit_sec_group")
@user_passes_test(GroupManager.can_manage_groups)
def group_manual_refresh(request, sg_id=None):
    logger.debug("group_manual_refresh called by user %s" % request.user)
    run_smart_group_update.apply_async(args=[sg_id], priority=4)
    sg = SmartGroup.objects.get(id=sg_id)

    messages.info(request, f"Added Priority job for '{sg.group.name}'")
    return redirect("securegroups:audit_list")


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
        request_info = request.user.username + ":" + group.name
        log = RequestLog(request_type=False, group=group,
                         request_info=request_info, action=1, request_actor=request.user)
        log.save()
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
    grouprequest.notify_leaders()
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
    if getattr(settings, "GROUPMANAGEMENT_AUTO_LEAVE", False) or getattr(settings, "AUTO_LEAVE", False):
        logger.info(
            "%s leaving joinable group %s due to auto_leave" % (
                request.user, group)
        )
        request_info = request.user.username + ":" + group.name
        log = RequestLog(request_type=True, group=group,
                         request_info=request_info, action=1, request_actor=request.user)
        log.save()
        request.user.groups.remove(group)
        return redirect("securegroups:groups")
    grouprequest = GroupRequest()
    grouprequest.status = _("Pending")
    grouprequest.group = group
    grouprequest.user = request.user
    grouprequest.leave_request = True
    grouprequest.save()
    grouprequest.notify_leaders()
    logger.info(
        "Created group leave request for user %s to group %s"
        % (request.user, Group.objects.get(id=group_id))
    )
    messages.success(request, _(
        "Applied to leave group %(group)s.") % {"group": group})
    return redirect("securegroups:groups")


@permission_required("securegroups.audit_sec_group")
@user_passes_test(GroupManager.can_manage_groups)
def group_membership_remove(request, group_id, user_id):
    logger.debug("group_membership_remove called by user %s for group id %s on user id %s" % (
        request.user, group_id, user_id))
    group = get_object_or_404(Group, id=group_id)
    try:
        # Check its a joinable group i.e. not corp or internal
        # And the user has permission to manage it
        if not GroupManager.check_internal_group(group) or not GroupManager.can_manage_group(request.user, group):
            logger.warning("User %s attempted to remove a user from group %s but permission was denied" % (
                request.user, group_id))
            raise PermissionDenied

        try:
            user = group.user_set.get(id=user_id)
            request_info = user.username + ":" + group.name
            log = RequestLog(request_type=None, group=group,
                             request_info=request_info, action=1, request_actor=request.user)
            log.save()
            # Remove group from user
            user.groups.remove(group)
            logger.info("User %s removed user %s from group %s" %
                        (request.user, user, group))
            return JsonResponse({"user_id": user.pk})
        except ObjectDoesNotExist:
            return Http404("Does not Exist")

    except ObjectDoesNotExist:
        return Http404("Does not Exist")
