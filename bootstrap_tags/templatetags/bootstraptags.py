from django import template

register = template.Library()

counter = 0


@register.simple_tag
def url_replace(request, field, value):
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()


@register.inclusion_tag("bootstrap_tags/pagination.html")
def bs_pagination(page, request, **kwargs):
    pages_before_after = 3
    current_page = page.number
    pages_before = min(current_page - 1, pages_before_after)
    pages_after = min(page.paginator.num_pages - current_page,
                      pages_before_after)
    start_page = current_page - pages_before
    end_page = current_page + pages_after
    return {'page': page, 'page_range': range(start_page, end_page + 1),
            'request': request}


@register.inclusion_tag("bootstrap_tags/alert.html")
def bs_alert(alert_type, alert_text, **kwargs):
    dismissible = kwargs.get('dismissible', False)
    return {'alert_type': alert_type, 'alert_text': alert_text,
            'dismissible': dismissible}
