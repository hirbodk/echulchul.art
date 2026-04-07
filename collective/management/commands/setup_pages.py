"""
Creates the required Wagtail page tree for the collective app:
  / (HomePage, already exists)
  ├── /artists/  (ArtistIndexPage)
  └── /works/    (ArtWorkIndexPage)

Safe to run multiple times — skips pages that already exist.
"""
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site

from collective.models import ArtistIndexPage, ArtWorkIndexPage
from home.models import HomePage


class Command(BaseCommand):
    help = 'Create the initial collective page tree (artists + works index pages)'

    def handle(self, *args, **options):
        home = HomePage.objects.first()
        if not home:
            self.stderr.write('No HomePage found — run migrations first.')
            return

        self._ensure(home, ArtistIndexPage, slug='artists', title='Artists')
        self._ensure(home, ArtWorkIndexPage, slug='works',   title='Works')

        # Make sure the default Site points to the root page
        site = Site.objects.first()
        if site and site.root_page_id != home.pk:
            site.root_page = home
            site.save()
            self.stdout.write(f'Site root updated to: {home}')

        self.stdout.write(self.style.SUCCESS('Page tree ready.'))

    def _ensure(self, parent, page_type, slug, title):
        if page_type.objects.filter(slug=slug).exists():
            self.stdout.write(f'  skip  {slug}/ (already exists)')
            return
        page = page_type(title=title, slug=slug, show_in_menus=True)
        parent.add_child(instance=page)
        page.save_revision().publish()
        self.stdout.write(f'  created  /{slug}/')
