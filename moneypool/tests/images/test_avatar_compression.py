"""Avatars are stored at display size, not at camera resolution."""

import io

from PIL import Image

import pytest

from moneypool.domain.images import AVATAR_MAX_SIDE, compress_avatar, within_avatar_bounds


def make_image(size, mode='RGB', fmt='JPEG', exif=None):
    image = Image.new(mode, size, (180, 90, 40) if mode == 'RGB' else (180, 90, 40, 255))
    buf = io.BytesIO()
    if exif is not None:
        image.save(buf, fmt, exif=exif)
    else:
        image.save(buf, fmt)
    return buf.getvalue()


def opened(data):
    return Image.open(io.BytesIO(data))


class TestCompressAvatar:
    @pytest.mark.parametrize('size', [(4032, 3024), (3024, 4032), (1206, 2622), (1646, 1646)])
    def test_the_longest_side_is_brought_within_bounds(self, size):
        out = opened(compress_avatar(make_image(size)))

        assert max(out.size) <= AVATAR_MAX_SIDE

    def test_aspect_ratio_is_kept(self):
        out = opened(compress_avatar(make_image((4000, 2000))))

        assert out.size[0] / out.size[1] == pytest.approx(2.0, abs=0.02)

    def test_a_png_with_transparency_becomes_a_jpeg(self):
        # JPEG cannot carry an alpha channel, and screenshots in the bucket are RGBA
        out = opened(compress_avatar(make_image((1646, 1654), mode='RGBA', fmt='PNG')))

        assert out.format == 'JPEG'
        assert out.mode == 'RGB'

    def test_an_image_smaller_than_the_bound_is_not_enlarged(self):
        out = opened(compress_avatar(make_image((100, 120))))

        assert out.size == (100, 120)

    def test_a_camera_sized_photo_shrinks_by_more_than_ten_times(self):
        raw = make_image((4032, 3024))

        assert len(compress_avatar(raw)) * 10 < len(raw)

    def test_rotation_recorded_in_exif_is_applied(self):
        # Orientation 6 means "rotate 90 degrees". A portrait photo stored as
        # landscape-plus-a-tag comes out sideways if this is ignored, which is
        # the way this change is most likely to ship looking wrong.
        exif = Image.Exif()
        exif[0x0112] = 6
        raw = make_image((400, 200), exif=exif)

        out = opened(compress_avatar(raw))

        assert out.size[1] > out.size[0], 'exif orientation was not applied'

    def test_compression_is_idempotent(self):
        once = compress_avatar(make_image((4032, 3024)))
        twice = compress_avatar(once)

        assert opened(twice).size == opened(once).size


class TestWithinAvatarBounds:
    def test_a_camera_photo_is_not_within_bounds(self):
        assert within_avatar_bounds(make_image((4032, 3024))) is False

    def test_a_large_png_is_not_within_bounds_even_when_small_on_disk(self):
        assert within_avatar_bounds(make_image((300, 300), fmt='PNG')) is False

    def test_a_compressed_avatar_is_within_bounds(self):
        assert within_avatar_bounds(compress_avatar(make_image((4032, 3024)))) is True
