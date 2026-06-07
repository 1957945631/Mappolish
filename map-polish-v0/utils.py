from dataclasses import dataclass
from pathlib import Path


MAX_IMAGE_BYTES = 10 * 1024 * 1024
SUPPORTED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


@dataclass(frozen=True)
class ImageValidation:
    extension: str
    size_bytes: int


def validate_image_upload(filename: str, image_bytes: bytes) -> ImageValidation:
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only PNG, JPG, JPEG, and WEBP images are supported.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("Image size must be 10MB or smaller.")
    return ImageValidation(extension=extension, size_bytes=len(image_bytes))
