import io

import pillow_heif
from PIL import Image, ImageOps

# iPhones shoot HEIC by default, and neither Pillow nor any browser decodes it
# without help. Registering the opener lets Image.open treat it like any other
# format, which is what turns an unusable upload into a normal one.
pillow_heif.register_heif_opener()

AVATAR_MAX_SIDE = 512
AVATAR_QUALITY = 82


def compress_avatar(data: bytes, max_side: int = AVATAR_MAX_SIDE, quality: int = AVATAR_QUALITY) -> bytes:
    """Scale an uploaded picture down to an avatar and re-encode it as JPEG."""
    image = Image.open(io.BytesIO(data))
    # rotation lives in EXIF on phone photos; without this the result is sideways
    image = ImageOps.exif_transpose(image)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image.thumbnail((max_side, max_side), Image.LANCZOS)

    out = io.BytesIO()
    image.save(out, format='JPEG', quality=quality, optimize=True)
    return out.getvalue()


def within_avatar_bounds(data: bytes, max_side: int = AVATAR_MAX_SIDE) -> bool:
    """Whether the picture is already an avatar-sized JPEG."""
    image = Image.open(io.BytesIO(data))
    return image.format == 'JPEG' and max(image.size) <= max_side
