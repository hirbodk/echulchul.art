# echulchul.art — Data Model Design

## Overview

The `collective` app is a flat, graph-ready model that replaces the old
`portfolio` hierarchy (Collection → Project → ArtPiece).

Artworks are the only core content objects. Grouping is dynamic via
query-based Collections. Relations between artworks live as typed
key-value attributes on artworks.

---

## Model diagram

```
AttributeKey  (Wagtail snippet)
  name: CharField unique  e.g. "finished_date", "status", "related_work"
  vtype: string | number | boolean | date | artwork
  description: TextField

ArtworkAttribute  (inline on Artwork)
  artwork  → Artwork  (ParentalKey)
  key      → AttributeKey  (FK PROTECT)
  val_string:  CharField
  val_number:  FloatField
  val_boolean: BooleanField
  val_date:    DateField
  val_artwork  → Artwork FK   ← graph edge when vtype=artwork

Artwork  (Wagtail Page  →  /works/<slug>/)
  artists:    ParentalManyToManyField → ArtistPage
  tags:       TaggableManager  (django-taggit)
  body:       StreamField
                rich_text | image | audio | video_embed
                external_link | statement
  attributes: inline ArtworkAttribute

Collection  (Django model + view  →  /c/<slug>/)
  name, slug, description
  mode:     and | or
  sort_by:  title | first_published_at | <AttributeKey.name>
  sort_dir: asc | desc
  conditions → CollectionCondition
    field: __tag__ | __artist__ | <AttributeKey.name>
    op:    eq | neq | lt | gt | contains | includes
    value: string (coerced to attr type at query time)

  .get_artworks() — live QuerySet, always fresh

ArtistPage  (Wagtail Page  →  /artists/<slug>/)
  bio, photo, role, website, email
  → works: reverse M2M from Artwork.artists

FlexPage  (Wagtail Page  →  anywhere in tree)
  body: StreamField (richtext, image, embed, link)

HomePage  (Wagtail Page  →  /)
  tagline, intro (RichText)
  links: Orderable (label + url)
```

---

## URL structure

```
/                    HomePage
/artists/            ArtistIndexPage
/artists/<slug>/     ArtistPage
/works/              ArtWorkIndexPage  (tag/artist filter via ?tag=X&artist=Y)
/works/<slug>/       Artwork
/c/<slug>/           Collection (Django view — not a Wagtail page)
/about/              AboutPage (from home app, unchanged)
```

FlexPages live wherever in the Wagtail tree the editor places them.

---

## Future graph layer

When graph navigation is needed, no schema changes are required:

```python
# All directed artwork→artwork edges:
ArtworkAttribute.objects.filter(key__vtype='artwork')
# → each row is: artwork (source node), val_artwork (target node), key.name (edge label)
```

---

## Navigation modes (current)

| Mode | URL | How |
|---|---|---|
| Browse all works | `/works/` | tag + artist filter, grid |
| Browse by collection | `/c/<slug>/` | dynamic query result |
| Artist view | `/artists/<slug>/` | filtered works grid |
| Artwork detail | `/works/<slug>/` | body + attributes |
| Flex page | any slug | rich editorial content |

---

## CSS

All styles live in `echulchul/static/css/main.css`. The `collective` app
never rewrites this file — it only appends new classes at the bottom.
