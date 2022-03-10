from django.urls import re_path, include

from . import views

app_name = 'securegroups'

urlpatterns = [
    re_path(r'^$', views.groups_view, name='groups'),
    re_path(r'^audit/$', views.groups_manager_list, name='audit_list'),
    re_path(r'^audit/(?P<sg_id>(\d)*)/$',
            views.groups_manager_view, name='audit'),
    re_path(r'^audit/(?P<sg_id>(\d)*)/(?P<filter_id>(\d)*)/$',
            views.groups_manager_checks, name='audit_check'),

    re_path(r'^group/', include([
        re_path(r'^request_check/(?P<group_id>(\d)*)/$', views.smart_group_run_check,
            name='request_check'),
        re_path(r'^request_update/(?P<sg_id>(\d)*)/$', views.group_manual_refresh,
            name='update_group'),
        re_path(r'^request_add/(\w+)', views.group_request_add,
            name='request_add'),
        re_path(r'^request_leave/(\w+)', views.group_request_leave,
            name='request_leave'),
        re_path(r'^remove/(?P<group_id>(\d)*)/(?P<user_id>(\d)*)/$',
            views.group_membership_remove, name='rem_user'),
    ])
    ),
]
