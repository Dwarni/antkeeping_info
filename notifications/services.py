import re

from django.contrib.auth import get_user_model

from .models import (
    EntrySubscription,
    Notification,
    NotificationKind,
    NotificationPreference,
)

User = get_user_model()

MENTION_REGEX = re.compile(r"@([a-zA-Z0-9_.+-]+)")


def notify(
    recipient,
    kind,
    actor=None,
    entry=None,
    comment=None,
    colony=None,
    extra_data=None,
):
    """
    Central service to dispatch notifications.
    Enforces self-check, preferences, visibility, and like-grouping.
    """
    if not recipient or not recipient.is_authenticated:
        return None

    # Self-notification prevention
    if actor and actor.pk == recipient.pk:
        return None

    # In-app preference check
    if not NotificationPreference.is_enabled(recipient, kind, channel="in_app"):
        return None

    # Resolve colony
    target_colony = colony
    if not target_colony and entry:
        target_colony = getattr(entry, "colony", None)
    elif not target_colony and comment and getattr(comment, "entry", None):
        target_colony = getattr(comment.entry, "colony", None)

    # Visibility check: if colony is private, only owner or staff can receive
    if target_colony and hasattr(target_colony, "is_visible_publicly"):
        is_owner = target_colony.user_id == recipient.pk
        if (
            not target_colony.is_visible_publicly
            and not is_owner
            and not recipient.is_staff
        ):
            return None

    # Muted thread check for THREAD_REPLY
    if kind == NotificationKind.THREAD_REPLY and entry:
        if EntrySubscription.objects.filter(
            user=recipient, entry=entry, muted=True
        ).exists():
            return None

    # Grouping for likes on journal entries
    if kind == NotificationKind.ENTRY_LIKED and entry:
        group_key = f"like:entry:{entry.pk}"
        existing = Notification.objects.filter(
            recipient=recipient,
            kind=kind,
            group_key=group_key,
            read_at__isnull=True,
        ).first()

        if existing:
            if actor:
                existing.actors.add(actor)
                existing.actor = actor
            if extra_data:
                merged_data = dict(existing.extra_data)
                merged_data.update(extra_data)
                existing.extra_data = merged_data
            existing.save()  # Triggers updated_at auto_now
            return existing
    else:
        group_key = ""

    notification = Notification.objects.create(
        recipient=recipient,
        kind=kind,
        actor=actor,
        entry=entry,
        comment=comment,
        colony=target_colony,
        group_key=group_key,
        extra_data=extra_data or {},
    )

    if actor:
        notification.actors.add(actor)

    return notification


def parse_mentions(text, max_mentions=10):
    """Extract mentioned usernames from text and return valid User instances."""
    if not text or "@" not in text:
        return []
    raw_matches = MENTION_REGEX.findall(text)
    if not raw_matches:
        return []

    # Preserve uniqueness while maintaining order
    seen = set()
    cleaned = []
    for uname in raw_matches:
        u_lower = uname.lower()
        if u_lower not in seen:
            seen.add(u_lower)
            cleaned.append(uname)
        if len(cleaned) >= max_mentions:
            break

    return list(User.objects.filter(username__in=cleaned))


def handle_like_toggled(entry, user, liked=True):
    """Trigger or clean up notification on journal entry like toggle."""
    if not entry or not user or not user.is_authenticated:
        return

    owner = entry.colony.user
    if liked:
        if owner != user:
            notify(
                recipient=owner,
                kind=NotificationKind.ENTRY_LIKED,
                actor=user,
                entry=entry,
                colony=entry.colony,
            )
    else:
        # Unlike: remove user from existing unread notification actors
        group_key = f"like:entry:{entry.pk}"
        notif = Notification.objects.filter(
            recipient=owner,
            kind=NotificationKind.ENTRY_LIKED,
            group_key=group_key,
            read_at__isnull=True,
        ).first()

        if notif:
            notif.actors.remove(user)
            remaining_actors = list(notif.actors.all())
            if not remaining_actors:
                notif.delete()
            else:
                notif.actor = remaining_actors[-1]
                notif.save(update_fields=["actor"])


def handle_comment_created(comment):
    """
    Called when a new comment is posted.
    Handles:
    1. Mentions (@username)
    2. Entry owner notification
    3. Thread participants notification
    4. Auto-subscribing the comment author to the entry
    """
    if not comment or not comment.entry:
        return

    entry = comment.entry
    author = comment.user
    colony = entry.colony

    notified_user_ids = {author.pk}

    # 1. Mentions
    mentioned_users = parse_mentions(comment.comment)
    for mentioned_user in mentioned_users:
        if mentioned_user.pk not in notified_user_ids:
            is_owner = colony.user_id == mentioned_user.pk
            if (
                not colony.is_visible_publicly
                and not is_owner
                and not mentioned_user.is_staff
            ):
                continue

            notify(
                recipient=mentioned_user,
                kind=NotificationKind.MENTIONED,
                actor=author,
                entry=entry,
                comment=comment,
                colony=colony,
            )
            notified_user_ids.add(mentioned_user.pk)

    # 2. Entry owner notification
    owner = colony.user
    if owner.pk not in notified_user_ids:
        notify(
            recipient=owner,
            kind=NotificationKind.ENTRY_COMMENTED,
            actor=author,
            entry=entry,
            comment=comment,
            colony=colony,
        )
        notified_user_ids.add(owner.pk)

    # 3. Thread participants (users who commented before or are subscribed)
    subscribed_ids = set(
        EntrySubscription.objects.filter(entry=entry, muted=False)
        .exclude(user_id__in=notified_user_ids)
        .values_list("user_id", flat=True)
    )
    from ants.models import ColonyJournalComment

    commenter_ids = set(
        ColonyJournalComment.objects.filter(entry=entry, is_removed=False)
        .exclude(user_id__in=notified_user_ids)
        .values_list("user_id", flat=True)
    )

    candidate_ids = (subscribed_ids | commenter_ids) - notified_user_ids
    if candidate_ids:
        muted_ids = set(
            EntrySubscription.objects.filter(
                entry=entry, user_id__in=candidate_ids, muted=True
            ).values_list("user_id", flat=True)
        )
        final_ids = candidate_ids - muted_ids

        participants = User.objects.filter(pk__in=final_ids)
        for participant in participants:
            is_owner = colony.user_id == participant.pk
            if (
                not colony.is_visible_publicly
                and not is_owner
                and not participant.is_staff
            ):
                continue

            notify(
                recipient=participant,
                kind=NotificationKind.THREAD_REPLY,
                actor=author,
                entry=entry,
                comment=comment,
                colony=colony,
            )

    # 4. Auto-subscribe comment author to thread
    EntrySubscription.objects.get_or_create(user=author, entry=entry)


def handle_comment_removed(comment, staff_user=None, reason=""):
    """Notify comment author if their comment was removed by a moderator."""
    if not comment or not comment.user:
        return

    notify(
        recipient=comment.user,
        kind=NotificationKind.COMMENT_REMOVED,
        actor=staff_user,
        entry=comment.entry,
        comment=comment,
        colony=comment.entry.colony if comment.entry else None,
        extra_data={"reason": reason or ""},
    )


def handle_colony_forced_private(colony, staff_user=None):
    """Notify colony owner if their colony was hidden by staff moderation."""
    if not colony or not colony.user:
        return

    notify(
        recipient=colony.user,
        kind=NotificationKind.COLONY_FORCED_PRIVATE,
        actor=staff_user,
        colony=colony,
    )
