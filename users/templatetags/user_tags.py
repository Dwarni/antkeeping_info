"""Template tags for users app."""

from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def user_avatar(user, size=32, css_class="", **kwargs):
    """
    Render a responsive, rounded avatar image for the user or a clean initial badge fallback.
    Accepts both css_class="..." and class="...".
    """
    if "class" in kwargs:
        css_class = kwargs["class"]

    try:
        size = int(size)
    except (ValueError, TypeError):
        size = 32

    font_size = max(11, int(size * 0.44))

    if user and user.is_authenticated:
        username = user.username or ""
        profile = getattr(user, "profile", None)
        if profile and profile.avatar:
            return format_html(
                '<img src="{}" alt="{}" class="rounded-circle {}" width="{}" height="{}" style="object-fit: cover; aspect-ratio: 1/1;">',
                profile.avatar.url,
                username,
                css_class,
                size,
                size,
            )

        initial = username[:1].upper() if username else "?"
        return format_html(
            '<span class="user-avatar-placeholder rounded-circle d-inline-flex align-items-center justify-content-center bg-primary-subtle text-primary fw-bold {}" '
            'style="width: {}px; height: {}px; min-width: {}px; font-size: {}px; line-height: 1;" title="@{}">{}</span>',
            css_class,
            size,
            size,
            size,
            font_size,
            username,
            initial,
        )

    return format_html(
        '<span class="user-avatar-placeholder rounded-circle d-inline-flex align-items-center justify-content-center bg-secondary-subtle text-secondary {}" '
        'style="width: {}px; height: {}px; min-width: {}px; font-size: {}px; line-height: 1;"><i class="bi bi-person-fill"></i></span>',
        css_class,
        size,
        size,
        size,
        font_size,
    )
