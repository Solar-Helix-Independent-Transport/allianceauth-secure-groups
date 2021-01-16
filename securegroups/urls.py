from django.conf.urls import url, include

from . import views

app_name = 'securegroups'

urlpatterns = [
    url(r'^$', views.groups_view, name='groups'),
    url(r'^group/', include([
        url(r'^request_check/(?P<group_id>(\d)*)/$', views.smart_group_run_check,
            name='request_check'),
        url(r'^request_add/(\w+)', views.group_request_add,
            name='request_add'),
        url(r'^request_leave/(\w+)', views.group_request_leave,
            name='request_leave'),
    ])
    ),
]
