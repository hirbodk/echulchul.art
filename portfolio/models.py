import pymysql
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()

from django.db import models
from wagtail.models import Page, Orderable
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from modelcluster.fields import ParentalKey, ParentalManyToManyField


# -----------------------------------------------
# PEOPLE INDEX
# -----------------------------------------------
class PeopleIndexPage(Page):
    intro = RichTextField(blank=True)
    max_count = 1

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    subpage_types = ['portfolio.PersonPage']


# -----------------------------------------------
# PERSON
# -----------------------------------------------
class PersonPage(Page):
    bio = RichTextField(blank=True)
    photo = models.ForeignKey(
        'wagtailimages.Image',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    role = models.CharField(max_length=255, blank=True)

    parent_page_types = ['portfolio.PeopleIndexPage']
    subpage_types = []

    content_panels = Page.content_panels + [
        FieldPanel('role'),
        FieldPanel('photo'),
        FieldPanel('bio'),
    ]

    def get_context(self, request):
        context = super().get_context(request)
        # Collections this person is part of
        context['collections'] = CollectionPage.objects.filter(
            people=self
        ).live().public()
        # Projects this person is a collaborator on
        context['projects'] = ProjectPage.objects.filter(
            people=self
        ).live().public()
        return context


# -----------------------------------------------
# COLLECTION INDEX
# -----------------------------------------------
class CollectionIndexPage(Page):
    intro = RichTextField(blank=True)
    max_count = 1

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    subpage_types = ['portfolio.CollectionPage']


# -----------------------------------------------
# COLLECTION
# -----------------------------------------------
class CollectionPage(Page):
    description = RichTextField(blank=True)
    people = ParentalManyToManyField(
        'portfolio.PersonPage',
        blank=True,
        related_name='collections'
    )

    parent_page_types = ['portfolio.CollectionIndexPage']
    subpage_types = ['portfolio.ProjectPage']

    content_panels = Page.content_panels + [
        FieldPanel('description'),
        FieldPanel('people'),
    ]

    def get_context(self, request):
        context = super().get_context(request)
        context['projects'] = self.get_children().live().public().specific()
        return context


# -----------------------------------------------
# PROJECT
# -----------------------------------------------
class ProjectPage(Page):
    description = RichTextField(blank=True)
    people = ParentalManyToManyField(
        'portfolio.PersonPage',
        blank=True,
        related_name='projects'
    )

    parent_page_types = ['portfolio.CollectionPage']
    subpage_types = ['portfolio.ArtPiecePage']

    content_panels = Page.content_panels + [
        FieldPanel('description'),
        FieldPanel('people'),
    ]

    def get_context(self, request):
        context = super().get_context(request)
        context['art_pieces'] = self.get_children().live().public().specific()
        return context

    @property
    def collection(self):
        return self.get_parent().specific

    @property
    def thumbnail(self):
        # Return first image from first art piece that has a thumbnail
        for piece in self.get_children().live().specific():
            if hasattr(piece, 'thumbnail') and piece.thumbnail:
                return piece.thumbnail
        return None


# -----------------------------------------------
# ART PIECE
# -----------------------------------------------
class ArtPiecePage(Page):
    description = RichTextField(blank=True)
    thumbnail = models.ForeignKey(
        'wagtailimages.Image',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    artists = ParentalManyToManyField(
        'portfolio.PersonPage',
        blank=True,
        related_name='art_pieces'
    )
    body = StreamField([
        ('image', ImageChooserBlock()),
        ('text', blocks.RichTextBlock()),
        ('audio', blocks.StructBlock([
            ('title', blocks.CharBlock()),
            ('audio_file', blocks.URLBlock(help_text='URL to audio file')),
        ])),
        ('soundcloud', blocks.URLBlock(help_text='SoundCloud URL')),
        ('embed', blocks.RawHTMLBlock(help_text='Embed code e.g. p5js, video')),
    ], use_json_field=True, blank=True)

    parent_page_types = ['portfolio.ProjectPage']
    subpage_types = []

    content_panels = Page.content_panels + [
        FieldPanel('description'),
        FieldPanel('thumbnail'),
        FieldPanel('artists'),
        FieldPanel('body'),
    ]

    @property
    def project(self):
        return self.get_parent().specific

    def get_first_text_excerpt(self):
        for block in self.body:
            if block.block_type == 'text':
                from wagtail.rich_text import expand_db_html
                import re
                html = expand_db_html(str(block.value))
                text = re.sub('<[^>]+>', '', html)
                return text[:200]
        return None


# -----------------------------------------------
# ABOUT PAGE
# -----------------------------------------------
class AboutPage(Page):
    max_count = 1
    body = RichTextField(blank=True)
    photo = models.ForeignKey(
        'wagtailimages.Image',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    content_panels = Page.content_panels + [
        FieldPanel('photo'),
        FieldPanel('body'),
    ]