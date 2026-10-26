from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class NotificationKind(models.TextChoices):
    ENTRY_LIKED = "ENTRY_LIKED", _("Like on journal entry")
    ENTRY_COMMENTED = "ENTRY_COMMENTED", _("Comment on journal entry")
    THREAD_REPLY = "THREAD_REPLY", _("Reply in commented thread")
    MENTIONED = "MENTIONED", _("Mention in comment")
    NEW_FOLLOWER = "NEW_FOLLOWER", _("New follower")
    FOLLOWED_NEW_ENTRY = (
        "FOLLOWED_NEW_ENTRY",
        _("New entry from followed colony/keeper"),
    )
    COMMENT_REMOVED = "COMMENT_REMOVED", _("Comment removed by moderation")
    COLONY_FORCED_PRIVATE = (
        "COLONY_FORCED_PRIVATE",
        _("Colony set to private by moderation"),
    )


DEFAULT_NOTIFICATION_CHANNELS = {
    NotificationKind.ENTRY_LIKED: {"in_app": True, "email": False, "push": False},
    NotificationKind.ENTRY_COMMENTED: {"in_app": True, "email": True, "push": True},
    NotificationKind.THREAD_REPLY: {"in_app": True, "email": False, "push": True},
    NotificationKind.MENTIONED: {"in_app": True, "email": True, "push": True},
    NotificationKind.NEW_FOLLOWER: {"in_app": True, "email": False, "push": False},
    NotificationKind.FOLLOWED_NEW_ENTRY: {
        "in_app": True,
        "email": True,
        "push": False,
    },
    NotificationKind.COMMENT_REMOVED: {"in_app": True, "email": True, "push": False},
    NotificationKind.COLONY_FORCED_PRIVATE: {
        "in_app": True,
        "email": True,
        "push": False,
    },
}


class NotificationPreference(models.Model):
    """Per-user preferences for notification channels."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        verbose_name=_("User"),
    )
    kind = models.CharField(
        max_length=50,
        choices=NotificationKind.choices,
        verbose_name=_("Notification Kind"),
    )
    in_app = models.BooleanField(default=True, verbose_name=_("In-App / Bell"))
    email = models.BooleanField(default=True, verbose_name=_("E-Mail"))
    push = models.BooleanField(default=True, verbose_name=_("Push"))

    class Meta:
        verbose_name = _("Notification Preference")
        verbose_name_plural = _("Notification Preferences")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "kind"],
                name="unique_user_notification_preference",
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.kind}"

    @classmethod
    def is_enabled(cls, user, kind, channel="in_app"):
        """Check if a specific channel is enabled for a user & kind."""
        if not user or not user.is_authenticated:
            return False

        pref = cls.objects.filter(user=user, kind=kind).first()
        if pref:
            return getattr(pref, channel, True)

        default_map = DEFAULT_NOTIFICATION_CHANNELS.get(kind, {})
        return default_map.get(channel, True)


class EntrySubscription(models.Model):
    """Subscription tracking for journal threads."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="journal_entry_subscriptions",
        verbose_name=_("User"),
    )
    entry = models.ForeignKey(
        "ants.ColonyJournalEntry",
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name=_("Journal entry"),
    )
    muted = models.BooleanField(
        default=False,
        verbose_name=_("Muted"),
        help_text=_(
            "If checked, thread reply notifications for this entry are suppressed."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        verbose_name = _("Entry Subscription")
        verbose_name_plural = _("Entry Subscriptions")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "entry"],
                name="unique_user_entry_subscription",
            )
        ]

    def __str__(self):
        status = " [MUTED]" if self.muted else ""
        return f"{self.user.username} on Entry {self.entry_id}{status}"


class Notification(models.Model):
    """In-app and omnichannel notification record."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Recipient"),
    )
    kind = models.CharField(
        max_length=50,
        choices=NotificationKind.choices,
        verbose_name=_("Kind"),
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actor_notifications",
        verbose_name=_("Actor"),
    )
    actors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="grouped_notifications",
        verbose_name=_("Grouped Actors"),
    )
    entry = models.ForeignKey(
        "ants.ColonyJournalEntry",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("Journal Entry"),
    )
    comment = models.ForeignKey(
        "ants.ColonyJournalComment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("Comment"),
    )
    colony = models.ForeignKey(
        "ants.Colony",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("Colony"),
    )
    group_key = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
        verbose_name=_("Group Key"),
        help_text=_("Key used to cluster likes on the same target"),
    )
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Extra Data"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Read at"),
    )
    emailed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Emailed at"),
    )
    pushed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Pushed at"),
    )

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["recipient", "read_at", "-updated_at"]),
            models.Index(fields=["recipient", "group_key"]),
        ]

    def __str__(self):
        status = "read" if self.is_read else "unread"
        return f"{self.kind} for {self.recipient.username} ({status})"

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_as_read(self, save=True):
        if not self.read_at:
            self.read_at = timezone.now()
            if save:
                self.save(update_fields=["read_at"])

    def mark_as_unread(self, save=True):
        if self.read_at:
            self.read_at = None
            if save:
                self.save(update_fields=["read_at"])

    def get_target_url(self):
        if self.comment_id:
            try:
                if self.comment and self.comment.entry_id:
                    return (
                        self.comment.entry.get_absolute_url()
                        + f"#comment-{self.comment.pk}"
                    )
            except Exception:
                pass
        if self.entry_id:
            try:
                if self.entry:
                    return self.entry.get_absolute_url()
            except Exception:
                pass
        if self.colony_id:
            try:
                if self.colony:
                    return self.colony.get_absolute_url()
            except Exception:
                pass
        return reverse("user_profile_journals")

    @property
    def icon_class(self):
        mapping = {
            NotificationKind.ENTRY_LIKED: "bi-heart-fill text-danger",
            NotificationKind.ENTRY_COMMENTED: "bi-chat-left-text-fill text-primary",
            NotificationKind.THREAD_REPLY: "bi-chat-dots-fill text-info",
            NotificationKind.MENTIONED: "bi-at text-warning",
            NotificationKind.NEW_FOLLOWER: "bi-person-plus-fill text-success",
            NotificationKind.FOLLOWED_NEW_ENTRY: "bi-journal-plus text-success",
            NotificationKind.COMMENT_REMOVED: "bi-slash-circle-fill text-danger",
            NotificationKind.COLONY_FORCED_PRIVATE: (
                "bi-shield-exclamation text-warning"
            ),
        }
        return mapping.get(self.kind, "bi-bell-fill text-secondary")

    @property
    def title_and_message(self):
        """Returns (title, message) tuple formatted for UI presentation."""
        grouped_count = self.actors.count()
        if self.actor:
            if grouped_count > 2:
                others = grouped_count - 1
                actor_str = _("%(actor)s and %(count)d others") % {
                    "actor": self.actor.username,
                    "count": others,
                }
            elif grouped_count == 2:
                other_user = self.actors.exclude(pk=self.actor.pk).first()
                if other_user:
                    actor_str = f"{self.actor.username}, {other_user.username}"
                else:
                    actor_str = self.actor.username
            else:
                actor_str = self.actor.username
        else:
            actor_str = _("Someone")

        colony_name = ""
        if self.colony_id and self.colony:
            colony_name = self.colony.name
        elif self.entry_id and self.entry and self.entry.colony:
            colony_name = self.entry.colony.name

        if self.kind == NotificationKind.ENTRY_LIKED:
            title = _("New like")
            if colony_name:
                message = _("%(actors)s liked your journal entry for '%(colony)s'") % {
                    "actors": actor_str,
                    "colony": colony_name,
                }
            else:
                message = _("%(actors)s liked your journal entry") % {
                    "actors": actor_str
                }
        elif self.kind == NotificationKind.ENTRY_COMMENTED:
            title = _("New comment")
            message = _(
                "%(actor)s commented on your journal entry for '%(colony)s'"
            ) % {
                "actor": actor_str,
                "colony": colony_name,
            }
        elif self.kind == NotificationKind.THREAD_REPLY:
            title = _("New reply in thread")
            message = _(
                "%(actor)s replied in a journal entry discussion you joined"
            ) % {
                "actor": actor_str,
            }
        elif self.kind == NotificationKind.MENTIONED:
            title = _("You were mentioned")
            message = _("%(actor)s mentioned you in a comment") % {"actor": actor_str}
        elif self.kind == NotificationKind.NEW_FOLLOWER:
            title = _("New follower")
            message = _("%(actor)s started following your colony '%(colony)s'") % {
                "actor": actor_str,
                "colony": colony_name,
            }
        elif self.kind == NotificationKind.FOLLOWED_NEW_ENTRY:
            title = _("New journal entry")
            message = _("%(actor)s posted a new journal entry for '%(colony)s'") % {
                "actor": actor_str,
                "colony": colony_name,
            }
        elif self.kind == NotificationKind.COMMENT_REMOVED:
            title = _("Comment removed")
            reason = self.extra_data.get("reason", "")
            if reason:
                message = _(
                    "A comment you posted was removed by a moderator. "
                    "Reason: %(reason)s"
                ) % {"reason": reason}
            else:
                message = _("A comment you posted was removed by a moderator.")
        elif self.kind == NotificationKind.COLONY_FORCED_PRIVATE:
            title = _("Colony set to private")
            message = _(
                "Your colony '%(colony)s' was set to private by a moderator."
            ) % {"colony": colony_name}
        else:
            title = _("Notification")
            message = _("You have a new update.")

        return title, message
