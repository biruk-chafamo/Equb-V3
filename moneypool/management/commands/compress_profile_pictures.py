"""Re-encode already-uploaded profile pictures at avatar size."""

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from ...domain.images import compress_avatar, within_avatar_bounds
from ...models import User


class Command(BaseCommand):
    help = 'Shrink stored profile pictures to avatar size.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='report what would change without writing')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        users = User.objects.exclude(profile_picture='').exclude(profile_picture=None)

        skipped = failed = 0
        before = after = 0

        for user in users.iterator():
            picture = user.profile_picture
            try:
                picture.open('rb')
                data = picture.read()
            except Exception as error:
                # several rows point at keys that no longer exist in the bucket
                self.stderr.write(f'  unreadable  {user.username}: {error}')
                failed += 1
                continue
            finally:
                picture.close()

            if within_avatar_bounds(data):
                skipped += 1
                continue

            compressed = compress_avatar(data)
            before += len(data)
            after += len(compressed)
            name = picture.name.rsplit('/', 1)[-1].rsplit('.', 1)[0] + '.jpg'

            self.stdout.write(
                f'  {user.username:<20} {len(data) / 1e6:6.2f} MB -> {len(compressed) / 1000:5.0f} KB'
            )
            if not dry_run:
                # storage keeps file_overwrite off, so this writes a new key and
                # repoints the row; the original object stays in the bucket
                user.profile_picture.save(name, ContentFile(compressed), save=True)

        verb = 'would shrink' if dry_run else 'shrank'
        self.stdout.write(self.style.SUCCESS(
            f'\n{verb} {users.count() - skipped - failed} of {users.count()}: '
            f'{before / 1e6:.1f} MB -> {after / 1e6:.1f} MB '
            f'(already small: {skipped}, unreadable: {failed})'
        ))
