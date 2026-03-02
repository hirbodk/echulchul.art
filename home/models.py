from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel


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
    ]

    max_count = 1