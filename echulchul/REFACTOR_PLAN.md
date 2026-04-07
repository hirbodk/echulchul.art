# Rhizomatic Artist Collective Website — Refactor Plan

This document describes a full refactor of an existing Wagtail + Django website
toward a rhizomatic, graph-based architecture. Hand this file to a developer or
Claude Code instance as the authoritative specification.

---

## 1. Philosophy & Goals

The site models an artist collective whose works are related not by category or
authorship hierarchy, but by a web of conceptual, material, and explicit
editorial connections. The data is a **graph**. Navigation surfaces are multiple
**lenses** onto that graph — no single view is canonical, no structure is
primary.

Key principles:
- No hierarchy: an artwork is not "inside" an artist, collection, or category.
- Every artwork is a node; every relationship is an edge with a type and weight.
- Concepts (threads, mediums, forms) generate edges automatically. Artists can
  also author edges explicitly.
- Navigation modes are interchangeable entry points into the same underlying
  graph.
- Wagtail's page tree is a deployment detail only — it does not reflect the
  conceptual structure of the site.

---

## 2. Data Models

### 2.1 Concept

Replaces any previous `Medium`, `Tag`, `Category`, or `Collection` model.
Everything that was formerly a taxonomic label becomes a `Concept`.

```python
# collective/models.py

from django.db import models

class Concept(models.Model):
    CONCEPT_TYPES = [
        ('thread', 'Thread'),   # open, poetic — e.g. "displacement", "threshold"
        ('medium', 'Medium'),   # controlled vocab — e.g. "video", "sound", "text"
        ('form',   'Form'),     # structural — e.g. "series", "installation", "durational"
    ]

    name          = models.CharField(max_length=100, unique=True)
    concept_type  = models.CharField(max_length=20, choices=CONCEPT_TYPES, default='thread')
    description   = models.TextField(blank=True)
    rarity_weight = models.FloatField(default=1.0)
    # rarity_weight: curators can tune this manually.
    # High value = rare/precise concept = stronger graph attractor.
    # Optionally auto-compute as: 1 / log(1 + artworks.count())
    # and allow manual override.

    class Meta:
        ordering = ['concept_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.concept_type})"
```

**Migration notes:**
- If the existing site has `Tag` (django-taggit), `Medium`, or `Category`
  models, write a data migration that maps them into `Concept` rows with the
  appropriate `concept_type`.
- Remove `ClusterTaggableManager` and taggit through-models from `ArtWork`.
- Remove any existing `Medium` or `Category` ForeignKey/M2M from `ArtWork`.

---

### 2.2 Artist

Represents a person or collective who authors artworks. May already exist;
refactor as needed to match this spec.

```python
class Artist(models.Model):
    name        = models.CharField(max_length=255)
    bio         = models.TextField(blank=True)
    website     = models.URLField(blank=True)
    email       = models.EmailField(blank=True)
    # Optional: link to a Wagtail Page for a richer artist profile page
    profile_page = models.OneToOneField(
        'wagtailcore.Page',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='artist_profile'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
```

---

### 2.3 ArtWork

The central node of the graph. Registered as a Wagtail Page so it gets a URL,
admin editing, and preview support. All relational complexity lives in edges,
not in this model.

```python
from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel, InlinePanel, MultipleChooserPanel
from modelcluster.models import ClusterableModel
from modelcluster.fields import ParentalManyToManyField

class ArtWork(Page):
    # --- Core content ---
    body = StreamField([
        ('rich_text',    blocks.RichTextBlock()),
        ('image',        ImageChooserBlock()),
        ('audio',        AudioBlock()),          # custom block, see §4.1
        ('video_embed',  EmbedBlock()),
        ('external_link', LinkBlock()),          # custom block, see §4.1
        ('statement',    StatementBlock()),      # concept/artist statement, see §4.1
    ], use_json_field=True, blank=True)

    # --- Relations ---
    artists  = ParentalManyToManyField('Artist', blank=True, related_name='works')
    concepts = ParentalManyToManyField('Concept', blank=True, related_name='works')

    # --- Metadata ---
    year        = models.PositiveIntegerField(null=True, blank=True)
    location    = models.CharField(max_length=255, blank=True)
    # coordinates for map view (optional)
    geo_lat     = models.FloatField(null=True, blank=True)
    geo_lon     = models.FloatField(null=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('artists'),
        FieldPanel('body'),
        FieldPanel('concepts'),
        FieldPanel('year'),
        FieldPanel('location'),
        InlinePanel('explicit_edges_as_a', label='Connections to other works'),
    ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.rebuild_concept_edges()

    def rebuild_concept_edges(self):
        """
        Recomputes all concept-type ArtworkEdge rows involving this artwork.
        Called automatically on save. Safe to call multiple times (idempotent).
        """
        from django.db.models import Q, Avg

        # Delete stale concept edges for this artwork
        ArtworkEdge.objects.filter(
            edge_type='concept'
        ).filter(
            Q(artwork_a=self) | Q(artwork_b=self)
        ).delete()

        my_concepts = set(self.concepts.values_list('id', flat=True))
        if not my_concepts:
            return

        for other in ArtWork.objects.live().exclude(pk=self.pk):
            their_concepts = set(other.concepts.values_list('id', flat=True))
            shared = my_concepts & their_concepts
            if not shared:
                continue

            union   = my_concepts | their_concepts
            jaccard = len(shared) / len(union)

            rarity_boost = Concept.objects.filter(
                pk__in=shared
            ).aggregate(avg=Avg('rarity_weight'))['avg'] or 1.0

            weight = round(jaccard * rarity_boost, 4)

            shared_names = ", ".join(
                Concept.objects.filter(pk__in=shared)
                               .order_by('name')
                               .values_list('name', flat=True)
            )

            # Always store with lower pk as artwork_a to avoid duplicate edges
            a, b = (self, other) if self.pk < other.pk else (other, self)

            ArtworkEdge.objects.update_or_create(
                artwork_a=a,
                artwork_b=b,
                edge_type='concept',
                defaults={'weight': weight, 'label': shared_names}
            )

    class Meta:
        verbose_name        = 'Artwork'
        verbose_name_plural = 'Artworks'
```

**Migration notes:**
- If existing site has artworks as non-Page Django models, write a data
  migration to promote them to Wagtail Pages under a dedicated index page.
- If existing artworks use taggit tags for medium/concept, migrate those to
  `Concept` M2M (see §2.1 migration notes).

---

### 2.4 ArtworkEdge

The single unified edge model. Covers both artist-authored explicit connections
and system-generated concept connections.

```python
EDGE_TYPE_CHOICES = [
    ('explicit', 'Explicit'),
    ('concept',  'Concept-generated'),
]

EXPLICIT_RELATION_CHOICES = [
    ('responds_to',   'Responds to'),
    ('echoes',        'Echoes'),
    ('contradicts',   'Contradicts'),
    ('continues',     'Continues'),
    ('departs_from',  'Departs from'),
    ('shares_site',   'Same site / location'),
    ('in_dialogue',   'In dialogue with'),
    ('precedes',      'Precedes'),
    ('other',         'Other (see notes)'),
]

class ArtworkEdge(models.Model):
    artwork_a = models.ForeignKey(
        ArtWork, on_delete=models.CASCADE, related_name='edges_as_a'
    )
    artwork_b = models.ForeignKey(
        ArtWork, on_delete=models.CASCADE, related_name='edges_as_b'
    )
    edge_type        = models.CharField(max_length=20, choices=EDGE_TYPE_CHOICES)
    label            = models.CharField(max_length=300, blank=True)
    # For explicit edges: one of EXPLICIT_RELATION_CHOICES (store as label)
    # For concept edges: comma-separated shared concept names (auto-set)
    weight           = models.FloatField(default=1.0)
    # For explicit edges: default 1.0; curators may set higher for strong links
    # For concept edges: Jaccard similarity × avg rarity_weight (auto-computed)
    notes            = models.TextField(blank=True)
    # Optional curatorial note visible on the connection itself
    is_directional   = models.BooleanField(default=False)
    # If True, artwork_a → artwork_b has direction (e.g. "responds_to")
    # If False, edge is symmetric

    class Meta:
        unique_together = [('artwork_a', 'artwork_b', 'edge_type', 'label')]
        ordering        = ['-weight']

    def __str__(self):
        return f"{self.artwork_a} —[{self.label}]→ {self.artwork_b}"

    @staticmethod
    def all_edges_for(artwork):
        """Return all edges touching this artwork, regardless of direction."""
        from django.db.models import Q
        return ArtworkEdge.objects.filter(
            Q(artwork_a=artwork) | Q(artwork_b=artwork)
        )

    @staticmethod
    def neighbour_ids_for(artwork, edge_types=None, min_weight=0.0):
        """Return list of (neighbour_artwork_id, edge) pairs."""
        from django.db.models import Q
        qs = ArtworkEdge.objects.filter(
            Q(artwork_a=artwork) | Q(artwork_b=artwork),
            weight__gte=min_weight
        )
        if edge_types:
            qs = qs.filter(edge_type__in=edge_types)
        results = []
        for edge in qs:
            neighbour = edge.artwork_b if edge.artwork_a_id == artwork.pk else edge.artwork_a
            results.append((neighbour, edge))
        return results
```

**Admin registration** — add to Wagtail snippets or use a custom ModelAdmin so
curators can inspect/edit all edges:

```python
# wagtail_hooks.py
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

class ArtworkEdgeAdmin(SnippetViewSet):
    model        = ArtworkEdge
    list_display = ['artwork_a', 'artwork_b', 'edge_type', 'label', 'weight']
    list_filter  = ['edge_type']
    search_fields = ['artwork_a__title', 'artwork_b__title', 'label']

register_snippet(ArtworkEdgeAdmin)
```

---

### 2.5 Plateau

An emergent or curated cluster of artworks. Not a folder. Not a category.
A Plateau has its own statement and sits alongside artworks as a peer, not above
them.

```python
class Plateau(Page):
    statement = RichTextField(blank=True)
    artworks  = ParentalManyToManyField(ArtWork, blank=True, related_name='plateaus')
    # Optional: a representative image for the plateau card
    cover_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    content_panels = Page.content_panels + [
        FieldPanel('statement'),
        FieldPanel('artworks'),
        FieldPanel('cover_image'),
    ]
```

A `Plateau` can be:
- **Curator-assembled**: editors pick artworks manually.
- **Algorithm-suggested**: a management command (see §5.2) can detect dense
  subgraphs (communities) in the edge graph and propose Plateau candidates for
  curator review.

---

### 2.6 Exhibition

A time-bound, event-like grouping. Has its own curatorial text, dates, and
location. May include artworks that aren't otherwise connected.

```python
class Exhibition(Page):
    subtitle     = models.CharField(max_length=255, blank=True)
    statement    = StreamField([...], use_json_field=True, blank=True)
    date_start   = models.DateField(null=True, blank=True)
    date_end     = models.DateField(null=True, blank=True)
    location     = models.CharField(max_length=255, blank=True)
    artworks     = ParentalManyToManyField(ArtWork, blank=True, related_name='exhibitions')
    cover_image  = models.ForeignKey(
        'wagtailimages.Image',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
```

---

## 3. URL Structure

Wagtail's page tree is used minimally — it provides URLs and the admin tree,
nothing more. Suggested tree layout:

```
/ (HomePage)
├── /works/             (ArtWorkIndexPage — lists all artworks)
│   └── /works/<slug>/  (ArtWork pages live here)
├── /plateaus/
│   └── /plateaus/<slug>/
├── /exhibitions/
│   └── /exhibitions/<slug>/
├── /artists/
│   └── /artists/<slug>/  (optional rich artist profile pages)
└── /graph/             (standalone graph view — served by a custom Django view)
```

No artwork is a child of an artist page. No artwork is a child of a plateau.
The tree is flat by design.

---

## 4. StreamField Blocks

### 4.1 Custom blocks for ArtWork.body

```python
# collective/blocks.py
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.embeds.blocks import EmbedBlock

class AudioBlock(blocks.StructBlock):
    title   = blocks.CharBlock(required=False)
    file    = blocks.URLBlock(help_text='URL to audio file or streaming embed')
    caption = blocks.CharBlock(required=False)

    class Meta:
        icon     = 'media'
        template = 'blocks/audio_block.html'

class LinkBlock(blocks.StructBlock):
    text = blocks.CharBlock()
    url  = blocks.URLBlock()
    note = blocks.CharBlock(required=False, help_text='Context for this link')

    class Meta:
        icon     = 'link'
        template = 'blocks/link_block.html'

class StatementBlock(blocks.StructBlock):
    """Artist/concept statement — styled distinctly from body text."""
    heading = blocks.CharBlock(required=False, help_text='e.g. "Artist statement"')
    body    = blocks.RichTextBlock()

    class Meta:
        icon     = 'openquote'
        template = 'blocks/statement_block.html'
```

---

## 5. API Endpoints

All navigation surfaces consume a small set of JSON endpoints. These are plain
Django views — no DRF required, though DRF can be used if already present.

### 5.1 Graph endpoint

`GET /api/graph/`

Query parameters:
- `edge_type` (repeatable): `explicit`, `concept`, or both (default: both)
- `concept_type` (repeatable): filter concept edges by concept type
- `min_weight` (float, default `0.0`): cull weak edges
- `artist` (int): only artworks by this artist id
- `concept` (int or name): only artworks sharing this concept

Response shape:
```json
{
  "nodes": [
    {
      "id": 42,
      "title": "Threshold Studies",
      "url": "/works/threshold-studies/",
      "year": 2021,
      "artists": ["Ana Folau"],
      "concepts": [
        {"name": "threshold", "type": "thread", "rarity_weight": 1.8},
        {"name": "video",     "type": "medium", "rarity_weight": 0.6}
      ],
      "plateaus": ["After the Event"],
      "thumbnail": "/media/images/threshold-thumb.jpg"
    }
  ],
  "edges": [
    {
      "a": 42,
      "b": 57,
      "type": "concept",
      "label": "threshold, forensic aesthetics",
      "weight": 0.72,
      "directional": false
    },
    {
      "a": 42,
      "b": 31,
      "type": "explicit",
      "label": "responds_to",
      "weight": 1.0,
      "notes": "Direct response to the 2019 piece",
      "directional": true
    }
  ]
}
```

Implementation sketch:
```python
# collective/views.py
import json
from django.http import JsonResponse
from django.db.models import Q
from .models import ArtWork, ArtworkEdge

def graph_json(request):
    edge_types   = request.GET.getlist('edge_type') or ['explicit', 'concept']
    concept_types = request.GET.getlist('concept_type')
    min_weight   = float(request.GET.get('min_weight', 0))
    artist_id    = request.GET.get('artist')
    concept_name = request.GET.get('concept')

    artworks = ArtWork.objects.live().prefetch_related(
        'artists', 'concepts', 'plateaus'
    )
    if artist_id:
        artworks = artworks.filter(artists__pk=artist_id)
    if concept_name:
        artworks = artworks.filter(concepts__name=concept_name)

    artwork_ids = set(artworks.values_list('pk', flat=True))

    nodes = []
    for a in artworks:
        thumb = None
        # Pull first image block from body if present
        for block in (a.body or []):
            if block.block_type == 'image' and block.value:
                thumb = block.value.get_rendition('fill-400x300').url
                break
        nodes.append({
            'id':       a.pk,
            'title':    a.title,
            'url':      a.url,
            'year':     a.year,
            'artists':  [ar.name for ar in a.artists.all()],
            'concepts': [
                {'name': c.name, 'type': c.concept_type, 'rarity_weight': c.rarity_weight}
                for c in a.concepts.all()
            ],
            'plateaus':  [p.title for p in a.plateaus.all()],
            'thumbnail': thumb,
        })

    edge_qs = ArtworkEdge.objects.filter(
        edge_type__in=edge_types,
        weight__gte=min_weight,
        artwork_a__in=artwork_ids,
        artwork_b__in=artwork_ids,
    )
    if concept_types:
        # Only keep concept edges where the shared concept matches concept_type
        # (requires a join — simplest approach: post-filter in Python)
        pass  # implement if needed

    edges = [
        {
            'a':           e.artwork_a_id,
            'b':           e.artwork_b_id,
            'type':        e.edge_type,
            'label':       e.label,
            'weight':      e.weight,
            'notes':       e.notes,
            'directional': e.is_directional,
        }
        for e in edge_qs
    ]

    return JsonResponse({'nodes': nodes, 'edges': edges})
```

Register in `urls.py`:
```python
path('api/graph/', views.graph_json, name='graph_json'),
```

### 5.2 Artwork detail endpoint (for drift mode)

`GET /api/artwork/<id>/neighbours/`

Returns the immediate neighbourhood of one artwork — used by drift mode to
load adjacent nodes without reloading the full graph.

```python
def artwork_neighbours(request, pk):
    artwork    = get_object_or_404(ArtWork, pk=pk)
    edge_types = request.GET.getlist('edge_type') or ['explicit', 'concept']
    min_weight = float(request.GET.get('min_weight', 0))

    neighbours = ArtworkEdge.neighbour_ids_for(artwork, edge_types, min_weight)
    return JsonResponse({
        'artwork': {'id': artwork.pk, 'title': artwork.title, 'url': artwork.url},
        'neighbours': [
            {
                'id':     n.pk,
                'title':  n.title,
                'url':    n.url,
                'edge':   {'type': e.edge_type, 'label': e.label, 'weight': e.weight}
            }
            for n, e in neighbours
        ]
    })
```

---

## 6. Navigation Modes

These are frontend surfaces — they consume the API endpoints above and render
different lenses onto the same graph. Each can be implemented as a standalone
page template with JavaScript, or as a React/Vue component served from a Wagtail
Page.

### 6.1 Graph View

**What it is:** A force-directed canvas showing all artworks as nodes and all
edges as lines. Spring simulation uses edge weight as spring stiffness — works
sharing rare concepts cluster tightly; loosely related works drift apart.

**Entry point:** `/graph/`

**Controls the visitor sees:**
- Toggle layers: `[explicit connections]` `[concept threads]` `[mediums]` `[forms]`
- Minimum weight slider (0 → 1) — culls weak edges to reveal structure
- Highlight by artist — dims everything not by selected artist
- Highlight by concept — dims everything not sharing this concept
- Click a node → goes to artwork detail page (or opens a sidebar preview)

**Implementation:**
- Use D3.js `forceSimulation` with `forceManyBody`, `forceLink` (strength =
  edge weight), `forceCenter`.
- Fetch `/api/graph/` on load with current filter params.
- Node size = number of edges (degree). More connected works are visually larger.
- Edge colour encodes type: explicit = saturated purple, concept = muted amber.
- Edge opacity encodes weight.
- On low-weight-threshold settings, distinct clusters become visible — these are
  candidate Plateaus.

**Performance notes:**
- Above ~300 nodes, cull concept edges below a threshold by default.
- Consider a WebGL renderer (e.g. `sigma.js` or `PixiJS`) for large collections.
- The `/api/graph/` endpoint should be cached (Django cache framework, 60s TTL)
  since it's read-heavy and changes only when artworks are saved.

---

### 6.2 Concept Trail View

**What it is:** A filtered gallery. Choose one or more concepts and see all
artworks that carry them. Multiple selected concepts show their union (OR) or
intersection (AND) — visitor-selectable.

**Entry point:** `/works/?concept=threshold` or `/works/?concept=threshold&concept=video`

**Controls:**
- Concept chips — click to add/remove from active filter set
- Union / Intersection toggle
- Filter by concept_type (show only threads, mediums, forms, or all)
- Sort by: year, title, connection density (number of edges)

**Implementation:**
- Standard Django ListView with `filter(concepts__name__in=[...])` and
  `.distinct()`.
- Concept chips rendered from `/api/graph/?concept=X` or from a
  `GET /api/concepts/` endpoint listing all concepts with artwork counts.
- No JavaScript required for basic version; HTMX or Alpine.js for live
  filtering without full page reloads.

**Concept index endpoint:**
```python
def concept_index(request):
    from django.db.models import Count
    concepts = Concept.objects.annotate(
        artwork_count=Count('works', distinct=True)
    ).filter(artwork_count__gt=0).order_by('concept_type', 'name')
    return JsonResponse({'concepts': [
        {'id': c.pk, 'name': c.name, 'type': c.concept_type,
         'count': c.artwork_count, 'weight': c.rarity_weight}
        for c in concepts
    ]})
```

---

### 6.3 Plateau View

**What it is:** Browse by emergent cluster. Each Plateau is a curated or
detected grouping with its own statement. Visitor sees a grid of Plateaus, each
showing a few representative artwork thumbnails.

**Entry point:** `/plateaus/`

**Within a Plateau page:**
- The plateau's statement / curatorial text
- Grid of member artworks
- "Neighbouring plateaus" — other Plateaus that share artworks with this one
  (computed as: `Plateau.objects.filter(artworks__in=self.artworks.all()).exclude(pk=self.pk).distinct()`)
- If the visitor came from the graph view, a "return to graph" link that
  re-focuses the graph on this plateau's subgraph

**Algorithm-suggested Plateaus (management command):**
```python
# management/commands/suggest_plateaus.py
# Uses a simple community detection heuristic on the edge graph.
# Outputs candidate Plateau records in draft state for curator review.
#
# Algorithm: Louvain or greedy modularity (use the `networkx` library).
# Steps:
#   1. Build networkx Graph from ArtworkEdge queryset
#   2. Run community detection
#   3. For each community of size >= MIN_SIZE, create a draft Plateau
#      with artworks = community members
#   4. Print summary for curator review
```

---

### 6.4 Drift Mode

**What it is:** Serendipitous single-artwork navigation. Land on any artwork,
see its direct neighbours (all edge types), follow one. No back-button pressure.
No search. Pure movement through the graph.

**Entry point:** Any artwork page, via a "drift" toggle or a dedicated `/drift/`
starting URL that picks a random artwork.

**UX flow:**
1. Artwork page renders its content normally.
2. Below (or in a sidebar): a "neighbours" panel showing 3–6 connected artworks,
   each with: thumbnail, title, the edge label connecting them
   (e.g. "echoes", "shared: threshold, forensic aesthetics").
3. Clicking a neighbour navigates to that artwork and the panel refreshes.
4. An optional "random jump" button picks a random artwork from the full graph
   (useful if the visitor has reached a node with few connections).

**Implementation:**
- Fetch `/api/artwork/<id>/neighbours/` on each page load.
- Render neighbour panel via a small JavaScript snippet or HTMX partial.
- The `min_weight` for drift mode should be lower than graph view default
  (say 0.1) to ensure most artworks have at least some neighbours.
- Edge label shown to visitor: for explicit edges, show the human-readable
  relation label; for concept edges, show the shared concept names.

**Drift start view:**
```python
import random
def drift_start(request):
    pks     = list(ArtWork.objects.live().values_list('pk', flat=True))
    artwork = ArtWork.objects.get(pk=random.choice(pks))
    return redirect(artwork.url + '?drift=1')
```

---

### 6.5 Artist View

**What it is:** A per-artist index — not a hierarchy, just a filter. Shows all
artworks by one artist, their collaborators (other artists they share artworks
with), and the concept cloud of their practice.

**Entry point:** `/artists/<slug>/`

**Page content:**
- Artist bio
- Grid of their artworks
- Collaborators: other artists appearing in the same artworks
- Concept cloud: all concepts across their works, sized by frequency
- "Works in conversation with": artworks by *other* artists that have explicit
  edges to this artist's works (cross-artist connections)

---

### 6.6 Exhibition View

**What it is:** A time-indexed curatorial view. Exhibitions are the one place
where a traditional "show" concept applies — a group of works presented
together at a specific time and place.

**Entry point:** `/exhibitions/`

**Within an Exhibition page:**
- Curatorial statement (StreamField)
- Dates and location
- Participating works (grid)
- Participating artists (derived from works)
- "Related plateaus" — Plateaus that overlap with this exhibition's artworks

---

## 7. Wagtail Admin UX for Artists

The editing experience for artists adding works should feel light and
rhizomatics-first. Suggested admin panel ordering for `ArtWork`:

1. **Title** — the work's name
2. **Body** — StreamField (rich content)
3. **Artists** — M2M chooser (search by name)
4. **Concepts** — M2M chooser, grouped by concept_type in the UI
5. **Year / Location / Coordinates** — metadata
6. **Connections** — InlinePanel for explicit `ArtworkEdge` rows where this
   artwork is `artwork_a`. Each row: choose the other artwork, choose the
   relation label, set weight, add optional notes.

**Suggested connections feature (optional enhancement):**
After saving, a Wagtail `after_edit_page` hook can POST to a view that returns
top-5 concept-edge neighbours not yet explicitly connected. These appear in the
admin as "suggested connections" the artist can confirm and label.

```python
# wagtail_hooks.py
from wagtail import hooks

@hooks.register('after_edit_page')
def suggest_connections(request, page):
    if not isinstance(page, ArtWork):
        return
    # compute top concept neighbours, store as session variable
    # admin template includes a suggestion panel reading from session
    pass
```

---

## 8. Management Commands

### 8.1 Rebuild all concept edges

Run after bulk imports, concept rarity_weight changes, or concept renames.

```bash
python manage.py rebuild_concept_edges
```

```python
# management/commands/rebuild_concept_edges.py
from django.core.management.base import BaseCommand
from collective.models import ArtWork, ArtworkEdge

class Command(BaseCommand):
    help = 'Rebuild all concept-type ArtworkEdge rows from scratch'

    def handle(self, *args, **options):
        ArtworkEdge.objects.filter(edge_type='concept').delete()
        artworks = list(ArtWork.objects.live().prefetch_related('concepts'))
        self.stdout.write(f'Processing {len(artworks)} artworks...')
        for artwork in artworks:
            artwork.rebuild_concept_edges()
        self.stdout.write(self.style.SUCCESS('Done.'))
```

### 8.2 Auto-compute rarity weights

Recalculates `Concept.rarity_weight` as `1 / log(1 + artwork_count)` for all
concepts, unless manually overridden.

```bash
python manage.py recompute_rarity_weights
```

### 8.3 Suggest plateaus

```bash
python manage.py suggest_plateaus --min-size=4 --min-weight=0.3
```

Requires `networkx` (`pip install networkx`). Creates draft Plateau pages for
curator review.

---

## 9. Migration Checklist

Work through this list in order when refactoring an existing site:

- [ ] Install dependencies: `networkx` (optional, for plateau detection)
- [ ] Create `Concept` model and migration
- [ ] Write data migration: map existing tags/mediums/categories → `Concept` rows
- [ ] Create `ArtworkEdge` model and migration
- [ ] Add `concepts` M2M to `ArtWork`; remove old tag/medium fields
- [ ] Add `artists` M2M to `ArtWork` (if not already present)
- [ ] Write data migration: populate `ArtWork.concepts` from old tags
- [ ] Create `Plateau` model and migration
- [ ] Create `Exhibition` model and migration (or refactor existing)
- [ ] Write `rebuild_concept_edges` management command and run it
- [ ] Register `ArtworkEdge`, `Concept`, `Plateau` in Wagtail admin
- [ ] Add `/api/graph/` endpoint and connect to URL conf
- [ ] Add `/api/artwork/<id>/neighbours/` endpoint
- [ ] Add `/api/concepts/` endpoint
- [ ] Build graph view frontend (D3.js or sigma.js)
- [ ] Build concept trail filter UI
- [ ] Build drift mode neighbour panel
- [ ] Add `suggest_plateaus` management command
- [ ] Set up caching on `/api/graph/` (Django cache framework)
- [ ] Test edge rebuild performance at scale (>200 artworks)
- [ ] Write tests for `rebuild_concept_edges` idempotency
- [ ] Write tests for `graph_json` filter parameters

---

## 10. Dependencies

```
# requirements additions
networkx>=3.0          # plateau community detection (optional)
# already present in Wagtail projects:
# wagtail, django, modelcluster, Pillow
```

No graph database (Neo4j etc.) is needed. Django's relational DB handles this
scale (hundreds to low thousands of artworks) comfortably with proper indexing.

Add indexes on `ArtworkEdge`:
```python
class Meta:
    indexes = [
        models.Index(fields=['artwork_a', 'edge_type']),
        models.Index(fields=['artwork_b', 'edge_type']),
        models.Index(fields=['edge_type', 'weight']),
    ]
```

---

## 11. Open Questions for the Collective

Before starting implementation, resolve these with the collective:

1. **Directionality**: Should explicit edges be directional by default
   (A responds to B ≠ B responds to A), or symmetric? The model supports both
   via `is_directional`, but the UI needs a consistent convention.

2. **Who can author explicit edges?** Only designated curators, or any member
   artist? If artists, do connections require approval before publishing?

3. **Concept vocabulary governance**: Who can add new Concepts? Free-for-all,
   or curator-approved? Consider a `is_approved` field on `Concept`.

4. **Plateau visibility**: Should algorithm-suggested Plateaus be visible to
   visitors immediately, or only after curator review?

5. **Graph view default state**: Should the graph load showing all artworks and
   all edge types, or start filtered (e.g. only explicit edges, or only works
   above a minimum connection density)?

6. **Drift mode UX**: Should drift remember the path (breadcrumb of visited
   works), or be fully amnesiac — always just showing the current work and its
   neighbours?

---

*End of plan. All models, endpoints, and navigation modes described here are
consistent with each other. Implement in the order given in §9.*
