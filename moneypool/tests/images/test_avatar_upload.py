"""An uploaded avatar is stored at display size, not as the camera produced it."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from PIL import Image

import pytest

from moneypool.domain.images import AVATAR_MAX_SIDE
from moneypool.tests.factories import UserFactory


def camera_photo(size=(4032, 3024), fmt='JPEG'):
    image = Image.new('RGB', size, (180, 90, 40))
    buf = io.BytesIO()
    image.save(buf, fmt, quality=100)
    return buf.getvalue()


@pytest.fixture
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.mark.django_db
class TestAvatarUpload:
    def test_a_camera_photo_is_stored_as_an_avatar(self, make_authed_client, media_root):
        user = UserFactory()
        client = make_authed_client(user)
        raw = camera_photo()

        response = client.patch(
            reverse('user-detail', args=[user.pk]),
            {'profile_picture': SimpleUploadedFile('IMG_4021.jpeg', raw, 'image/jpeg')},
            format='multipart',
        )

        assert response.status_code == 200, response.content[:200]
        user.refresh_from_db()
        stored = Image.open(user.profile_picture)
        assert max(stored.size) <= AVATAR_MAX_SIDE
        assert user.profile_picture.size * 10 < len(raw)

    def test_a_png_screenshot_is_stored_as_a_jpeg(self, make_authed_client, media_root):
        user = UserFactory()
        client = make_authed_client(user)

        response = client.patch(
            reverse('user-detail', args=[user.pk]),
            {'profile_picture': SimpleUploadedFile(
                'Screenshot.png', camera_photo((1646, 1654), 'PNG'), 'image/png')},
            format='multipart',
        )

        assert response.status_code == 200, response.content[:200]
        user.refresh_from_db()
        assert user.profile_picture.name.endswith('.jpg')
        assert Image.open(user.profile_picture).format == 'JPEG'

    def test_a_file_that_is_not_an_image_is_still_rejected(self, make_authed_client, media_root):
        user = UserFactory()
        client = make_authed_client(user)

        response = client.patch(
            reverse('user-detail', args=[user.pk]),
            {'profile_picture': SimpleUploadedFile('notes.txt', b'not an image', 'text/plain')},
            format='multipart',
        )

        assert response.status_code == 400
        assert 'profile_picture' in response.json()
