"""compress_profile_pictures re-encodes what is already in the bucket."""

import io

from django.core.files.base import ContentFile
from django.core.management import call_command

from PIL import Image

import pytest

from moneypool.domain.images import AVATAR_MAX_SIDE
from moneypool.tests.factories import UserFactory


def camera_photo(size=(4032, 3024)):
    buf = io.BytesIO()
    Image.new('RGB', size, (180, 90, 40)).save(buf, 'JPEG', quality=100)
    return buf.getvalue()


@pytest.fixture
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


def user_with_photo(size=(4032, 3024), name='IMG_9001.jpeg'):
    user = UserFactory()
    user.profile_picture.save(name, ContentFile(camera_photo(size)), save=True)
    return user


@pytest.mark.django_db
class TestBackfill:
    def test_an_oversized_picture_is_shrunk(self, media_root):
        user = user_with_photo()
        original = user.profile_picture.size

        call_command('compress_profile_pictures')

        user.refresh_from_db()
        assert max(Image.open(user.profile_picture).size) <= AVATAR_MAX_SIDE
        assert user.profile_picture.size * 10 < original

    def test_dry_run_changes_nothing(self, media_root):
        user = user_with_photo()
        before = user.profile_picture.name

        call_command('compress_profile_pictures', '--dry-run')

        user.refresh_from_db()
        assert user.profile_picture.name == before
        assert max(Image.open(user.profile_picture).size) > AVATAR_MAX_SIDE

    def test_running_twice_leaves_the_second_pass_with_nothing_to_do(self, media_root):
        user = user_with_photo()

        call_command('compress_profile_pictures')
        user.refresh_from_db()
        settled = user.profile_picture.name

        call_command('compress_profile_pictures')
        user.refresh_from_db()

        assert user.profile_picture.name == settled

    def test_a_user_without_a_picture_is_left_alone(self, media_root):
        user = UserFactory()

        call_command('compress_profile_pictures')

        user.refresh_from_db()
        assert not user.profile_picture

    def test_a_missing_object_does_not_stop_the_run(self, media_root):
        broken = user_with_photo()
        broken.profile_picture.storage.delete(broken.profile_picture.name)
        healthy = user_with_photo(name='IMG_9002.jpeg')

        call_command('compress_profile_pictures')

        healthy.refresh_from_db()
        assert max(Image.open(healthy.profile_picture).size) <= AVATAR_MAX_SIDE
