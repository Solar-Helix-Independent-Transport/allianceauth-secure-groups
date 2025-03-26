from django.template.defaulttags import register
from django.utils.safestring import mark_safe


@register.simple_tag()
def pass_fail(obj):
    output = False
    description = False
    if isinstance(obj, bool):
        if obj:
            output = True
    if isinstance(obj, list):
        if len(obj) > 0:
            output = True
            description = ", ".join(obj)

    if not output:
        return mark_safe(
            '<a class="btn btn-danger" type="button"><i class="fa-solid fa-times-circle"></i></a>'
        )
    else:
        if not description:
            description = ""
        return mark_safe(
            f'<a class="btn btn-success" type="button" data-bs-tooltip="allianceauth-secure-groups" title="{description}"><i class="fa-solid fa-check-circle"></i></a>'
        )
