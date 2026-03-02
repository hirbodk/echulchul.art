from django.db import models
from wagtail.models import Page, Orderable
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.models import ClusterableModel


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

    content_panels = Page.content_panels + [
        FieldPanel('role'),
        FieldPanel('photo'),
        FieldPanel('bio'),
    ]

    parent_page_types = ['portfolio.PeopleIndexPage']

    def get_context(self, request):
        context = super().get_context(request)
        from .models import ProjectPage
        context['projects'] = ProjectPage.objects.filter(
            people=self
        ).live().public()
        return context


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
    body = StreamField([
        ('image', ImageChooserBlock()),
        ('text', blocks.RichTextBlock()),
        ('audio', blocks.StructBlock([
            ('title', blocks.CharBlock()),
            ('audio_file', blocks.URLBlock(help_text='URL to audio file')),
        ])),
        ('soundcloud', blocks.URLBlock(help_text='SoundCloud embed URL')),
        ('embed', blocks.RawHTMLBlock(help_text='Any embed code e.g. p5js, video')),
    ], use_json_field=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('description'),
        FieldPanel('thumbnail'),
        FieldPanel('body'),
    ]

    parent_page_types = ['portfolio.ProjectPage']


# -----------------------------------------------
# PROJECT
# -----------------------------------------------
class ProjectPage(Page):
    description = RichTextField(blank=True)
    people = ParentalManyToManyField('portfolio.PersonPage', blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('description'),
        FieldPanel('people'),
    ]

    parent_page_types = ['portfolio.ProjectIndexPage']

    class Meta:
        verbose_name = 'Project'


# -----------------------------------------------
# ABOUT PAGE
# -----------------------------------------------
class AboutPage(Page):
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

class PeopleIndexPage(Page):
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    subpage_types = ['portfolio.PersonPage']  # only PersonPages can live under this

    class Meta:
        verbose_name = 'People Index'


class ProjectIndexPage(Page):
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    subpage_types = ['portfolio.ProjectPage']  # only ProjectPages can live under this

    class Meta:
        verbose_name = 'Projects Index'

        