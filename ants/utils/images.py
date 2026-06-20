"""Helpers for normalizing user-uploaded images before they hit storage."""

import io

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def downscale_to_max_dimension(file_field, max_dimension):
    """Shrink an uploaded image in place so its longest side is at most max_dimension.

    No-op if the image is already within bounds. Operates on a Django
    FieldFile that has a freshly-assigned upload (e.g. inside save()).
    """
    file_field.open()
    image = Image.open(file_field)
    image = ImageOps.exif_transpose(image)

    if max(image.width, image.height) <= max_dimension:
        return

    image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    buffer = io.BytesIO()
    save_format = image.format or "JPEG"
    if save_format == "JPEG" and image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(buffer, format=save_format, quality=85)

    file_field.save(file_field.name, ContentFile(buffer.getvalue()), save=False)
