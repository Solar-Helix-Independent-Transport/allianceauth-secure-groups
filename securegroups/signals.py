from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from . import models

# signals go here

from allianceauth import hooks


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


filters = hook_cache()


@receiver(post_save)
def new_filter(sender, instance, created, **kwargs):
    try:
        if instance.__class__ in filters.get_hooks():
            if created:
                models.SmartFilter.objects.create(filter_object=instance)
            else:
                # this is an updated model we dont at this stage care about this.
                pass
    except:
        print("Bah Humbug")  # we failed! do something here


@receiver(pre_delete)
def rem_filter(sender, instance, **kwargs):
    try:
        if instance.__class__ in filters.get_hooks():
            models.SmartFilter.objects.get(
                object_id=instance.pk, content_type__model=instance.__class__.__name__
            ).delete()
    except:
        print("Bah Humbug")  # we failed! do something here


@receiver(post_save, sender=models.SmartGroup)
def new_group_filter(sender, instance: models.SmartGroup, created, **kwargs):
    try:
        instance.group.authgroup.internal = False
        instance.group.authgroup.hidden = True
        instance.group.authgroup.public = False
        instance.group.save()
    except:
        print("Bah Humbug")  # we failed! do something here
