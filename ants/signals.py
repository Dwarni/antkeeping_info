from django.db.models.signals import post_delete
from django.dispatch import receiver

from ants.models import ColonyJournalEntryImage


@receiver(post_delete, sender=ColonyJournalEntryImage)
def delete_journal_entry_image_file(sender, instance, **kwargs):
    """Remove the image file from storage once its row is deleted.

    Runs on post_delete so it also fires for cascaded deletes (e.g. when
    the parent ColonyJournalEntry or Colony is deleted), not just explicit
    instance.delete() calls.
    """
    if instance.image_file:
        instance.image_file.delete(save=False)
