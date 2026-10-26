from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from ants.models import ColonyJournalEntry

from .models import (
    DEFAULT_NOTIFICATION_CHANNELS,
    EntrySubscription,
    Notification,
    NotificationKind,
    NotificationPreference,
)


@method_decorator(never_cache, name="dispatch")
class NotificationBadgeView(View):
    """HTMX polling endpoint returning the notification badge HTML."""

    def get(self, request):
        if not request.user.is_authenticated:
            return HttpResponse("")

        unread_count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count()

        response = render(
            request,
            "notifications/snippets/badge.html",
            {"unread_count": unread_count, "user": request.user},
        )
        response["HX-Trigger"] = f'{{"notificationCountUpdated": {unread_count}}}'
        return response


@method_decorator(never_cache, name="dispatch")
class NotificationDropdownView(View):
    """HTMX endpoint loaded when the notification bell dropdown is toggled."""

    def get(self, request):
        if not request.user.is_authenticated:
            return HttpResponse("")

        notifications = (
            Notification.objects.filter(recipient=request.user)
            .select_related("actor", "entry", "entry__colony", "comment", "colony")
            .prefetch_related("actors")[:10]
        )

        unread_count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count()

        return render(
            request,
            "notifications/snippets/dropdown.html",
            {
                "notifications": notifications,
                "unread_count": unread_count,
            },
        )


@method_decorator(never_cache, name="dispatch")
class NotificationListView(LoginRequiredMixin, View):
    """Full notifications inbox page with filter tabs and pagination."""

    def get(self, request):
        filter_type = request.GET.get("filter", "all")
        qs = (
            Notification.objects.filter(recipient=request.user)
            .select_related("actor", "entry", "entry__colony", "comment", "colony")
            .prefetch_related("actors")
        )

        if filter_type == "unread":
            qs = qs.filter(read_at__isnull=True)
        elif filter_type == "mentions":
            qs = qs.filter(kind=NotificationKind.MENTIONED)

        paginator = Paginator(qs, 20)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        unread_count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count()

        mentions_count = Notification.objects.filter(
            recipient=request.user,
            kind=NotificationKind.MENTIONED,
        ).count()

        context = {
            "page_obj": page_obj,
            "filter_type": filter_type,
            "unread_count": unread_count,
            "mentions_count": mentions_count,
            "total_count": Notification.objects.filter(recipient=request.user).count(),
        }

        if request.headers.get("HX-Request") and request.GET.get("page"):
            return render(
                request,
                "notifications/snippets/notification_page_items.html",
                context,
            )

        return render(request, "notifications/notification_list.html", context)


@method_decorator(never_cache, name="dispatch")
class NotificationOpenView(LoginRequiredMixin, View):
    """Mark a notification as read and redirect directly to its target URL."""

    def get(self, request, pk):
        notification = get_object_or_404(
            Notification.objects.select_related("entry", "comment", "colony"),
            pk=pk,
            recipient=request.user,
        )
        notification.mark_as_read()
        return redirect(notification.get_target_url())


@method_decorator(never_cache, name="dispatch")
class NotificationToggleReadView(LoginRequiredMixin, View):
    """Toggle or set read status for a notification."""

    def post(self, request, pk):
        notification = get_object_or_404(
            Notification.objects.select_related(
                "actor", "entry", "entry__colony", "comment", "colony"
            ).prefetch_related("actors"),
            pk=pk,
            recipient=request.user,
        )
        action = request.POST.get("action", "toggle")
        if action == "read":
            notification.mark_as_read()
        elif action == "unread":
            notification.mark_as_unread()
        else:
            if notification.is_read:
                notification.mark_as_unread()
            else:
                notification.mark_as_read()

        unread_count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count()

        if request.headers.get("HX-Request"):
            response = render(
                request,
                "notifications/snippets/notification_item.html",
                {
                    "notification": notification,
                    "title": notification.title_and_message[0],
                    "message": notification.title_and_message[1],
                },
            )
            response["HX-Trigger"] = f'{{"notificationCountUpdated": {unread_count}}}'
            return response

        return redirect(request.META.get("HTTP_REFERER", "notifications:list"))


@method_decorator(never_cache, name="dispatch")
class NotificationMarkAllReadView(LoginRequiredMixin, View):
    """Mark all unread notifications as read."""

    def post(self, request):
        Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).update(read_at=timezone.now())

        if request.headers.get("HX-Request"):
            next_url = request.POST.get("next", "")
            if next_url == "dropdown":
                notifications = (
                    Notification.objects.filter(recipient=request.user)
                    .select_related(
                        "actor", "entry", "entry__colony", "comment", "colony"
                    )
                    .prefetch_related("actors")[:10]
                )
                response = render(
                    request,
                    "notifications/snippets/dropdown.html",
                    {"notifications": notifications, "unread_count": 0},
                )
                response["HX-Trigger"] = '{"notificationCountUpdated": 0}'
                return response
            else:
                response = redirect(
                    request.META.get("HTTP_REFERER", "notifications:list")
                )
                response["HX-Trigger"] = '{"notificationCountUpdated": 0}'
                return response

        return redirect(request.META.get("HTTP_REFERER", "notifications:list"))


@method_decorator(never_cache, name="dispatch")
class NotificationDeleteView(LoginRequiredMixin, View):
    """Delete a notification."""

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.delete()

        unread_count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count()

        if request.headers.get("HX-Request"):
            response = HttpResponse("")
            response["HX-Trigger"] = f'{{"notificationCountUpdated": {unread_count}}}'
            return response

        return redirect(request.META.get("HTTP_REFERER", "notifications:list"))


@method_decorator(never_cache, name="dispatch")
class NotificationToggleThreadMuteView(LoginRequiredMixin, View):
    """Mute or unmute notifications for a specific journal entry thread."""

    def post(self, request, entry_pk):
        entry = get_object_or_404(ColonyJournalEntry, pk=entry_pk)
        sub, created = EntrySubscription.objects.get_or_create(
            user=request.user, entry=entry
        )
        sub.muted = not sub.muted
        sub.save(update_fields=["muted"])

        if request.headers.get("HX-Request"):
            return render(
                request,
                "notifications/snippets/mute_button.html",
                {"entry": entry, "is_muted": sub.muted},
            )

        return redirect(entry.get_absolute_url())


@method_decorator(never_cache, name="dispatch")
class NotificationSettingsView(LoginRequiredMixin, View):
    """Notification settings hub (in-app, email, push preference toggles)."""

    def get(self, request):
        user_prefs = {
            p.kind: p for p in NotificationPreference.objects.filter(user=request.user)
        }

        matrix = []
        for kind_choice, kind_label in NotificationKind.choices:
            defaults = DEFAULT_NOTIFICATION_CHANNELS.get(
                kind_choice, {"in_app": True, "email": False, "push": False}
            )
            saved = user_prefs.get(kind_choice)
            matrix.append(
                {
                    "kind": kind_choice,
                    "label": kind_label,
                    "in_app": saved.in_app if saved else defaults.get("in_app", True),
                    "email": saved.email if saved else defaults.get("email", False),
                    "push": saved.push if saved else defaults.get("push", False),
                }
            )

        return render(
            request,
            "notifications/notification_settings.html",
            {
                "matrix": matrix,
                "active_tab": "settings",
            },
        )

    def post(self, request):
        """HTMX endpoint to toggle individual preference switch."""
        kind = request.POST.get("kind")
        channel = request.POST.get("channel")
        enabled = request.POST.get("enabled") in ("1", "true", "on", True)

        if kind not in dict(NotificationKind.choices) or channel not in (
            "in_app",
            "email",
            "push",
        ):
            return HttpResponseBadRequest("Invalid kind or channel")

        defaults = DEFAULT_NOTIFICATION_CHANNELS.get(
            kind, {"in_app": True, "email": False, "push": False}
        )
        pref, _ = NotificationPreference.objects.get_or_create(
            user=request.user,
            kind=kind,
            defaults={
                "in_app": defaults.get("in_app", True),
                "email": defaults.get("email", False),
                "push": defaults.get("push", False),
            },
        )
        setattr(pref, channel, enabled)
        pref.save(update_fields=[channel])

        if request.headers.get("HX-Request"):
            return HttpResponse(
                '<span class="badge bg-success-subtle text-success-emphasis '
                'border border-success-subtle small px-2 py-1">'
                '<i class="bi bi-check2"></i> Saved</span>'
            )

        return redirect("notifications:settings")
