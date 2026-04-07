from django.db import models
from django.db.models import Q

from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.models import ClusterableModel
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase

from wagtail.models import Page, Orderable
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.snippets.models import register_snippet

from .blocks import ARTWORK_BODY_BLOCKS, FLEX_BODY_BLOCKS


# ─────────────────────────────────────────────
# Attribute key registry
# ─────────────────────────────────────────────

VTYPE_CHOICES = [
    ('string',  'String'),
    ('number',  'Number'),
    ('boolean', 'Boolean'),
    ('date',    'Date'),
    ('artwork', 'Artwork'),
]


@register_snippet
class AttributeKey(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    vtype       = models.CharField(max_length=20, choices=VTYPE_CHOICES, default='string')
    description = models.TextField(blank=True)

    panels = [
        FieldPanel('name'),
        FieldPanel('vtype'),
        FieldPanel('description'),
    ]

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.vtype})'


# ─────────────────────────────────────────────
# Artist pages
# ─────────────────────────────────────────────

class ArtistIndexPage(Page):
    intro = RichTextField(blank=True)

    max_count     = 1
    subpage_types = ['collective.ArtistPage']

    content_panels = Page.content_panels + [FieldPanel('intro')]

    def get_context(self, request):
        ctx = super().get_context(request)
        ctx['artists'] = ArtistPage.objects.live().order_by('title')
        return ctx


class ArtistPageLink(Orderable):
    page  = ParentalKey('collective.ArtistPage', on_delete=models.CASCADE, related_name='links')
    label = models.CharField(max_length=100)
    url   = models.CharField(max_length=255)

    panels = [FieldPanel('label'), FieldPanel('url')]


class ArtistPage(Page):
    bio     = RichTextField(blank=True)
    photo   = models.ForeignKey(
        'wagtailimages.Image', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )
    role    = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    email   = models.EmailField(blank=True)

    parent_page_types = ['collective.ArtistIndexPage']
    subpage_types     = ['collective.FlexPage']

    content_panels = Page.content_panels + [
        FieldPanel('role'),
        FieldPanel('photo'),
        FieldPanel('bio'),
        FieldPanel('website'),
        FieldPanel('email'),
        InlinePanel('links', label='Links'),
    ]

    def get_context(self, request):
        ctx = super().get_context(request)
        ctx['artworks'] = Artwork.objects.live().filter(artists=self).order_by('title')
        return ctx

    def __str__(self):
        return self.title


# ─────────────────────────────────────────────
# Artwork tag through-model
# ─────────────────────────────────────────────

class ArtworkTag(TaggedItemBase):
    content_object = ParentalKey(
        'collective.Artwork',
        on_delete=models.CASCADE,
        related_name='tagged_items',
    )


# ─────────────────────────────────────────────
# Artwork + attributes
# ─────────────────────────────────────────────

class ArtworkAttribute(Orderable):
    artwork     = ParentalKey('collective.Artwork', on_delete=models.CASCADE, related_name='attributes')
    key         = models.ForeignKey(AttributeKey, on_delete=models.PROTECT, related_name='+')
    val_string  = models.CharField(max_length=500, blank=True)
    val_number  = models.FloatField(null=True, blank=True)
    val_boolean = models.BooleanField(null=True, blank=True)
    val_date    = models.DateField(null=True, blank=True)
    val_artwork = models.ForeignKey(
        'collective.Artwork', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='referenced_by',
    )

    panels = [
        FieldPanel('key'),
        FieldPanel('val_string'),
        FieldPanel('val_number'),
        FieldPanel('val_boolean'),
        FieldPanel('val_date'),
        FieldPanel('val_artwork'),
    ]

    def value(self):
        vtype = self.key.vtype
        if vtype == 'string':  return self.val_string
        if vtype == 'number':  return self.val_number
        if vtype == 'boolean': return self.val_boolean
        if vtype == 'date':    return self.val_date
        if vtype == 'artwork': return self.val_artwork
        return None

    def __str__(self):
        return f'{self.key.name}: {self.value()}'


class ArtWorkIndexPage(Page):
    intro = RichTextField(blank=True)

    max_count     = 1
    subpage_types = ['collective.Artwork']

    content_panels = Page.content_panels + [FieldPanel('intro')]

    def get_context(self, request):
        ctx = super().get_context(request)
        artworks = Artwork.objects.live().order_by('title')

        tag    = request.GET.get('tag')
        artist = request.GET.get('artist')

        if tag:
            artworks = artworks.filter(tags__name=tag)
        if artist:
            artworks = artworks.filter(artists__slug=artist)

        ctx['artworks']    = artworks.distinct()
        ctx['active_tag']  = tag
        ctx['active_artist'] = artist
        ctx['all_tags']    = _tag_cloud()
        ctx['all_artists'] = ArtistPage.objects.live().order_by('title')
        return ctx


class Artwork(Page):
    artists = ParentalManyToManyField('collective.ArtistPage', blank=True, related_name='works')
    tags    = ClusterTaggableManager(through=ArtworkTag, blank=True)
    body    = StreamField(ARTWORK_BODY_BLOCKS, use_json_field=True, blank=True)

    parent_page_types = ['collective.ArtWorkIndexPage']
    subpage_types     = []

    content_panels = Page.content_panels + [
        FieldPanel('artists'),
        FieldPanel('tags'),
        FieldPanel('body'),
        InlinePanel('attributes', label='Attributes'),
    ]

    def get_first_image(self):
        for block in (self.body or []):
            if block.block_type == 'image' and block.value:
                return block.value
        return None

    def get_text_excerpt(self, chars=200):
        import re
        for block in (self.body or []):
            if block.block_type == 'rich_text':
                text = re.sub(r'<[^>]+>', '', str(block.value))
                return text[:chars]
        return ''

    def __str__(self):
        return self.title


# ─────────────────────────────────────────────
# Collection (dynamic query-based grouping)
# ─────────────────────────────────────────────

OP_CHOICES = [
    ('eq',       'equals'),
    ('neq',      'not equals'),
    ('lt',       'less than'),
    ('gt',       'greater than'),
    ('contains', 'contains'),
    ('includes', 'includes'),
]


@register_snippet
class Collection(ClusterableModel):
    name        = models.CharField(max_length=255)
    slug        = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    mode        = models.CharField(max_length=3, choices=[('and', 'AND'), ('or', 'OR')], default='and')
    sort_by     = models.CharField(max_length=100, default='title',
                                   help_text='title, first_published_at, or an AttributeKey name')
    sort_dir    = models.CharField(max_length=4, choices=[('asc', 'asc'), ('desc', 'desc')], default='asc')

    panels = [
        FieldPanel('name'),
        FieldPanel('slug'),
        FieldPanel('description'),
        MultiFieldPanel([FieldPanel('mode'), FieldPanel('sort_by'), FieldPanel('sort_dir')], heading='Query'),
        InlinePanel('conditions', label='Conditions'),
    ]

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_artworks(self):
        qs = Artwork.objects.live()
        conditions = list(self.conditions.all())

        if not conditions:
            return qs.none()

        filters = [_condition_q(c) for c in conditions]
        combined = filters[0]
        for f in filters[1:]:
            combined = combined & f if self.mode == 'and' else combined | f

        qs = qs.filter(combined).distinct()

        prefix = '-' if self.sort_dir == 'desc' else ''
        if self.sort_by in ('title', 'first_published_at', 'last_published_at'):
            qs = qs.order_by(f'{prefix}{self.sort_by}')
        # attribute-based sort: fallback to title for now

        return qs


def _condition_q(condition):
    field, op, raw = condition.field, condition.op, condition.value

    if field == '__tag__':
        return Q(tags__name=raw)

    if field == '__artist__':
        return Q(artists__slug=raw)

    try:
        key = AttributeKey.objects.get(name=field)
    except AttributeKey.DoesNotExist:
        return Q(pk__in=[])

    vtype     = key.vtype
    val_col   = 'val_artwork__slug' if vtype == 'artwork' else f'val_{vtype}'
    coerced   = _coerce(raw, vtype)
    base_key  = {'attributes__key__name': field}

    if op == 'eq':       return Q(**base_key, **{f'attributes__{val_col}': coerced})
    if op == 'neq':      return ~Q(**base_key, **{f'attributes__{val_col}': coerced})
    if op == 'lt':       return Q(**base_key, **{f'attributes__{val_col}__lt': coerced})
    if op == 'gt':       return Q(**base_key, **{f'attributes__{val_col}__gt': coerced})
    if op == 'contains': return Q(**base_key, **{f'attributes__{val_col}__icontains': coerced})
    if op == 'includes': return Q(**base_key, **{f'attributes__{val_col}': coerced})
    return Q(pk__in=[])


def _coerce(value, vtype):
    if vtype == 'number':
        try: return float(value)
        except ValueError: return value
    if vtype == 'boolean':
        return value.lower() in ('true', '1', 'yes')
    return value


class CollectionCondition(models.Model):
    collection = ParentalKey(Collection, on_delete=models.CASCADE, related_name='conditions')
    field      = models.CharField(max_length=100, help_text='__tag__, __artist__, or AttributeKey name')
    op         = models.CharField(max_length=20, choices=OP_CHOICES, default='eq')
    value      = models.CharField(max_length=500)

    panels = [
        FieldPanel('field'),
        FieldPanel('op'),
        FieldPanel('value'),
    ]

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.field} {self.op} {self.value}'


# ─────────────────────────────────────────────
# FlexPage
# ─────────────────────────────────────────────

class FlexPage(Page):
    body = StreamField(FLEX_BODY_BLOCKS, use_json_field=True, blank=True)

    content_panels = Page.content_panels + [FieldPanel('body')]


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _tag_cloud():
    from taggit.models import Tag
    from django.db.models import Count
    return (
        Tag.objects
        .filter(collective_artworktag_items__isnull=False)
        .annotate(count=Count('collective_artworktag_items'))
        .order_by('-count')
    )
