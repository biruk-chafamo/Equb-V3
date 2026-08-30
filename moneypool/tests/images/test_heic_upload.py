"""iPhone photos arrive as HEIC, which nothing in the stack decodes by default."""

import io
import subprocess
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from PIL import Image

import pytest

from moneypool.domain.images import AVATAR_MAX_SIDE, compress_avatar
from moneypool.tests.factories import UserFactory


@pytest.fixture(scope='module')
def heic_bytes():
    """A real HEIC file, built with the macOS encoder."""
    with tempfile.TemporaryDirectory() as tmp:
        source, out = f'{tmp}/src.jpg', f'{tmp}/photo.heic'
        Image.new('RGB', (3024, 4032), (200, 120, 60)).save(source, 'JPEG', quality=95)
        result = subprocess.run(['sips', '-s', 'format', 'heic', source, '--out', out],
                                capture_output=True)
        if result.returncode != 0:
            pytest.skip('no HEIC encoder available on this machine')
        return open(out, 'rb').read()


@pytest.fixture
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


def test_a_heic_photo_can_be_decoded(heic_bytes):
    out = Image.open(io.BytesIO(compress_avatar(heic_bytes)))

    assert out.format == 'JPEG'
    assert max(out.size) <= AVATAR_MAX_SIDE


def test_a_heic_photo_keeps_its_orientation(heic_bytes):
    # the source is portrait; a decoder that ignores HEIC's rotation flips it
    out = Image.open(io.BytesIO(compress_avatar(heic_bytes)))

    assert out.size[1] > out.size[0]


@pytest.mark.django_db
def test_uploading_a_heic_photo_succeeds(make_authed_client, media_root, heic_bytes):
    user = UserFactory()
    client = make_authed_client(user)

    response = client.patch(
        reverse('user-detail', args=[user.pk]),
        # the web client mislabels everything that is not png as jpeg
        {'profile_picture': SimpleUploadedFile('IMG_1234.HEIC', heic_bytes, 'image/jpeg')},
        format='multipart',
    )

    assert response.status_code == 200, response.content[:200]
    user.refresh_from_db()
    assert user.profile_picture.name.endswith('.jpg')
    assert max(Image.open(user.profile_picture).size) <= AVATAR_MAX_SIDE


@pytest.mark.django_db
def test_a_genuinely_broken_file_is_still_rejected(make_authed_client, media_root):
    user = UserFactory()
    client = make_authed_client(user)

    response = client.patch(
        reverse('user-detail', args=[user.pk]),
        {'profile_picture': SimpleUploadedFile('notes.txt', b'not an image at all', 'image/jpeg')},
        format='multipart',
    )

    assert response.status_code == 400
    assert 'profile_picture' in response.json()
