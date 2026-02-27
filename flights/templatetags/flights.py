from django.template.defaulttags import register


@register.filter
def percentage(value, max_value):
    return (value / max_value) * 100
