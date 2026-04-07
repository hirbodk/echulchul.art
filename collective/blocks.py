from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.embeds.blocks import EmbedBlock


class AudioBlock(blocks.StructBlock):
    title   = blocks.CharBlock(required=False)
    file    = blocks.URLBlock(help_text='URL to audio file')
    caption = blocks.CharBlock(required=False)

    class Meta:
        icon     = 'media'
        template = 'collective/blocks/audio.html'


class LinkBlock(blocks.StructBlock):
    text = blocks.CharBlock()
    url  = blocks.URLBlock()
    note = blocks.CharBlock(required=False)

    class Meta:
        icon     = 'link'
        template = 'collective/blocks/link.html'


class StatementBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False)
    body    = blocks.RichTextBlock()

    class Meta:
        icon     = 'openquote'
        template = 'collective/blocks/statement.html'


ARTWORK_BODY_BLOCKS = [
    ('rich_text',    blocks.RichTextBlock()),
    ('image',        ImageChooserBlock()),
    ('audio',        AudioBlock()),
    ('video_embed',  EmbedBlock()),
    ('external_link', LinkBlock()),
    ('statement',    StatementBlock()),
]

FLEX_BODY_BLOCKS = [
    ('rich_text',    blocks.RichTextBlock()),
    ('image',        ImageChooserBlock()),
    ('video_embed',  EmbedBlock()),
    ('external_link', LinkBlock()),
]
