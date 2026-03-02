from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel
from modelcluster.fields import ParentalKey
from wagtail.models import Orderable


class HomePageLink(Orderable):
    page = ParentalKey('home.HomePage', on_delete=models.CASCADE, related_name='links')
    label = models.CharField(max_length=100)
    url = models.CharField(max_length=255)

    panels = [
        FieldPanel('label'),
        FieldPanel('url'),
    ]


class HomePage(Page):
    tagline = models.CharField(
        max_length=255,
        blank=True,
        default='Art Collective'
    )
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('tagline'),
        FieldPanel('intro'),
        MultiFieldPanel([
            InlinePanel('links', label='Link'),
        ], heading='Navigation Links'),
    ]

    max_count = 1