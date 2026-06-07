import unittest

from utils import MAX_IMAGE_BYTES, validate_image_upload


class UtilsTest(unittest.TestCase):
    def test_validate_image_upload_accepts_supported_format_under_size_limit(self):
        result = validate_image_upload("map.PNG", b"small image")

        self.assertEqual(result.extension, "png")
        self.assertEqual(result.size_bytes, len(b"small image"))


    def test_validate_image_upload_rejects_unsupported_format(self):
        with self.assertRaisesRegex(ValueError, "Only PNG, JPG, JPEG, and WEBP"):
            validate_image_upload("map.gif", b"small image")


    def test_validate_image_upload_rejects_file_over_10mb(self):
        oversized = b"x" * (MAX_IMAGE_BYTES + 1)

        with self.assertRaisesRegex(ValueError, "10MB"):
            validate_image_upload("map.jpg", oversized)


if __name__ == "__main__":
    unittest.main()
