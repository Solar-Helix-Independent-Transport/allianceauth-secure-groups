from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver, Signal
from django.db import transaction
from django.contrib.auth.models import User

from . import models

# signals go here

from allianceauth import hooks

import logging

logger = logging.getLogger(__name__)


class hook_cache:
    all_hooks = None

    def get_hooks(self):
        if self.all_hooks is None:
            hook_array = set()
            _hooks = hooks.get_hooks("secure_group_filters")
            for app_hook in _hooks:
                for filter_model in app_hook():
                    if filter_model not in hook_array:
                        hook_array.add(filter_model)
            self.all_hooks = hook_array
        return self.all_hooks


class group_cache:
    _user_groups = {}

    def set_user(self, user: User):
        self._user_groups[user.id] = set(
            user.groups.all().values_list('id', flat=True))

    def get_user(self, user: User):
        return self._user_groups.get(user.id, set())

    def clear_user(self, user: User):
        try:
            del self._user_groups[user.id]
            return True
        except KeyError:
            return False


signal_cache = group_cache()
filters = hook_cache()


def new_filter(sender, instance, created, **kwargs):
    try:
        if created:
            models.SmartFilter.objects.create(filter_object=instance)
        else:
            # this is an updated model we dont at this stage care about this.
            pass
    except:
        logger.error("Bah Humbug")  # we failed! do something here


def rem_filter(sender, instance, **kwargs):
    try:
        models.SmartFilter.objects.get(
            object_id=instance.pk, content_type__model=instance.__class__.__name__
        ).delete()
    except:
        logger.error("Bah Humbug")  # we failed! do something here


@receiver(post_save, sender=models.SmartGroup)
def new_group_filter(sender, instance: models.SmartGroup, created, **kwargs):
    try:
        instance.group.authgroup.internal = False
        instance.group.authgroup.hidden = True
        instance.group.authgroup.public = False
        instance.group.save()
    except:
        logger.error("Bah Humbug")  # we failed! do something here


for _filter in filters.get_hooks():
    post_save.connect(new_filter, sender=_filter)
    pre_delete.connect(rem_filter, sender=_filter)


@receiver(m2m_changed, sender=User.groups.through)
def m2m_changed_user_groups(sender, instance: User, action, *args, **kwargs):
    logger.debug("Received m2m_changed from %s groups with action %s" %
                 (instance, action))

    def trigger_group_checks():
        logger.debug("Checking user is valid for SmartGroups! %s" % instance)
        # find the groups!
        users_groups = instance.groups.filter(smartgroup__isnull=False)
        old_groups = signal_cache.get_user(instance)
        groups_to_remove = []
        for g in users_groups:
            if g.id not in old_groups:
                sg_check = g.smartgroup.check_user(instance)
                if not sg_check:
                    groups_to_remove.append(g)
                    logger.warning(
                        "Removing {} from {}, due to invalid join".format(instance, g))
        if len(groups_to_remove) > 0:
            instance.groups.remove(*groups_to_remove)
        signal_cache.clear_user(instance)

    if instance.pk and (action == "post_add"):
        logger.debug(
            "Waiting for commit to Checking user is valid for SmartGroups! %s" % instance)
        transaction.on_commit(trigger_group_checks)

    if instance.pk and (action == "pre_add"):
        signal_cache.set_user(instance)
