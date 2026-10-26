from django.contrib import admin

from .models import EntrySubscription, Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "kind",
        "actor",
        "colony",
        "entry",
        "read_at",
        "updated_at",
    )
    list_filter = ("kind", "read_at", "created_at")
    search_fields = ("recipient__username", "actor__username", "group_key")
    raw_id_fields = ("recipient", "actor", "entry", "comment", "colony")
    readonly_fields = ("created_at", "updated_at")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "in_app", "email", "push")
    list_filter = ("kind", "in_app", "email", "push")
    search_fields = ("user__username",)


@admin.register(EntrySubscription)
class EntrySubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "entry", "muted", "created_at")
    list_filter = ("muted", "created_at")
    search_fields = ("user__username", "entry__colony__name")
    raw_id_fields = ("user", "entry")
