from django.conf.urls import url, include

from . import views

app_name = 'securegroups'

urlpatterns = [
    url(r'^$', views.groups_view, name='groups'),
    url(r'^audit/$', views.groups_manager_list, name='audit_list'),
    url(r'^audit/(?P<sg_id>(\d)*)/$', views.groups_manager_view, name='audit'),
    url(r'^audit/(?P<sg_id>(\d)*)/(?P<filter_id>(\d)*)/$',
        views.groups_manager_checks, name='audit_check'),

    url(r'^group/', include([
        url(r'^request_check/(?P<group_id>(\d)*)/$', views.smart_group_run_check,
            name='request_check'),
        url(r'^request_update/(?P<sg_id>(\d)*)/$', views.group_manual_refresh,
            name='update_group'),
        url(r'^request_add/(\w+)', views.group_request_add,
            name='request_add'),
        url(r'^request_leave/(\w+)', views.group_request_leave,
            name='request_leave'),
        url(r'^remove/(?P<group_id>(\d)*)/(?P<user_id>(\d)*)/$',
            views.group_membership_remove, name='rem_user'),
    ])
    ),
]
