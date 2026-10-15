"""
Models module for users app.
"""

import io
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps


def validate_avatar_size(image):
    """Validate that the avatar image file size does not exceed 5MB."""
    max_size = 5 * 1024 * 1024  # 5 MB
    if hasattr(image, "size") and image.size > max_size:
        raise ValidationError(_("Avatar image file size cannot exceed 5 MB."))


def optimize_avatar_image(image_field_file, max_dimension=512):
    """
    Ensure the avatar image is square-cropped, downscaled to max 512x512,
    EXIF-oriented, and converted to WebP format with quality 85.
    """
    try:
        if hasattr(image_field_file, "seek"):
            image_field_file.seek(0)
        img = Image.open(image_field_file)
        img = ImageOps.exif_transpose(img)

        # Convert palette/CMYK to RGBA or RGB
        if img.mode in ("P", "LA"):
            img = img.convert("RGBA")
        elif img.mode in ("CMYK", "YCbCr"):
            img = img.convert("RGB")

        # Center crop to square if not already square
        w, h = img.size
        if w != h:
            min_dim = min(w, h)
            left = (w - min_dim) // 2
            top = (h - min_dim) // 2
            img = img.crop((left, top, left + min_dim, top + min_dim))

        # Downscale if larger than max_dimension
        if img.width > max_dimension or img.height > max_dimension:
            img = img.resize((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        out_io = io.BytesIO()
        img.save(out_io, format="WEBP", quality=85, method=4)
        out_io.seek(0)

        raw_name = getattr(image_field_file, "name", "avatar") or "avatar"
        base_name = os.path.splitext(os.path.basename(raw_name))[0]
        return ContentFile(out_io.getvalue(), name=f"{base_name}.webp")
    except Exception:
        if hasattr(image_field_file, "seek"):
            image_field_file.seek(0)
        return image_field_file


class UserProfile(models.Model):
    """User profile extension containing avatar, bio, and privacy settings."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("User"),
    )
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        blank=True,
        null=True,
        validators=[validate_avatar_size],
        verbose_name=_("Avatar"),
        help_text=_("Upload a square profile photo (JPG, PNG or WebP, max 5MB)."),
    )
    bio = models.TextField(
        blank=True,
        max_length=500,
        verbose_name=_("Bio"),
        help_text=_("A short bio about yourself and your ant colonies."),
    )
    location = models.CharField(
        blank=True,
        max_length=100,
        verbose_name=_("Location"),
        help_text=_("City or Country (optional)."),
    )
    show_full_name = models.BooleanField(
        default=False,
        verbose_name=_("Show full name publicly"),
        help_text=_(
            "If enabled, your first and last name will be shown publicly. "
            "If disabled, only your nickname (@username) is displayed."
        ),
    )
    show_location = models.BooleanField(
        default=True,
        verbose_name=_("Show location publicly"),
        help_text=_(
            "Display your approximate location/country on your public profile."
        ),
    )
    show_bio = models.BooleanField(
        default=True,
        verbose_name=_("Show bio publicly"),
        help_text=_("Display your 'About Me' bio on your public profile."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        return f"Profile of {self.user.username}"

    def save(self, *args, **kwargs):
        if (
            self.avatar
            and hasattr(self.avatar, "file")
            and not getattr(self.avatar, "_committed", True)
        ):
            optimized = optimize_avatar_image(self.avatar)
            if optimized and optimized is not self.avatar:
                self.avatar.save(optimized.name, optimized, save=False)
        super().save(*args, **kwargs)

    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, "url"):
            return self.avatar.url
        return None

    @property
    def display_name(self):
        if self.show_full_name:
            full = f"{self.user.first_name} {self.user.last_name}".strip()
            if full:
                return full
        return f"@{self.user.username}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Automatically ensure every user has an associated UserProfile."""
    UserProfile.objects.get_or_create(user=instance)
