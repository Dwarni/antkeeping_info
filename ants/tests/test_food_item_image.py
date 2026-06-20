import io
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image as PILImage

from ants.models import FoodItem

_MEDIA_ROOT = tempfile.mkdtemp()


def _make_upload(width, height, name="photo.jpg", fmt="JPEG"):
    buffer = io.BytesIO()
    PILImage.new("RGB", (width, height), color="red").save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class FoodItemImageResizeTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def test_oversized_image_is_downscaled_to_max_dimension(self):
        item = FoodItem.objects.create(
            name="Big photo",
            category=FoodItem.PROTEIN,
            image=_make_upload(3000, 1500),
        )
        item.refresh_from_db()
        with PILImage.open(item.image.path) as saved:
            self.assertEqual(max(saved.size), FoodItem.MAX_IMAGE_DIMENSION)
            self.assertEqual(saved.size, (1920, 960))

    def test_small_image_is_left_untouched(self):
        item = FoodItem.objects.create(
            name="Small photo",
            category=FoodItem.PROTEIN,
            image=_make_upload(400, 300),
        )
        item.refresh_from_db()
        with PILImage.open(item.image.path) as saved:
            self.assertEqual(saved.size, (400, 300))

    def test_resaving_unchanged_image_does_not_reprocess(self):
        item = FoodItem.objects.create(
            name="Stable photo",
            category=FoodItem.PROTEIN,
            image=_make_upload(3000, 1500),
        )
        item.refresh_from_db()

        with patch("ants.models.downscale_to_max_dimension") as mock_downscale:
            item.description = "Updated description"
            item.save()
            mock_downscale.assert_not_called()
