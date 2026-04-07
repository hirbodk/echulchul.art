# Runbook — echulchul.art

## Local development

### First-time setup

```bash
# Create and activate virtualenv
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Apply migrations (creates a fresh SQLite DB)
python manage.py migrate

# Create an admin user (username: admin, password: admin)
python manage.py createsuperuser --username admin --email admin@local.test --no-input
python manage.py shell -c "from django.contrib.auth.models import User; u=User.objects.get(username='admin'); u.set_password('admin'); u.save()"
```

Local admin credentials: **username** `admin` / **password** `admin`

### Run the dev server

```bash
source .venv/bin/activate   # if not already active
python manage.py runserver
```

Site: http://127.0.0.1:8000  
Admin: http://127.0.0.1:8000/admin/

### Set up the page tree (first time only)

```bash
python manage.py setup_pages
```

This creates `/artists/` and `/works/` index pages under the HomePage automatically.
Then go to **Snippets → Attribute Keys** to add any custom fields you want
(e.g. `year` as Number, `status` as String).

---

## Content editing guide

### Adding an Artist

1. **Admin → Pages → Home** — click the ✏️ next to **Artists**
2. **Add child page → Artist Page**
3. Fill in: Title (name), Role, Photo, Bio
4. **Publish**

Artist is now live at `/artists/<slug>/`

---

### Adding an Artwork

1. **Admin → Pages → Home** — click the ✏️ next to **Works**
2. **Add child page → Artwork**
3. Fill in:
   - **Title** — name of the work
   - **Artists** — pick one or more artists (must exist first)
   - **Tags** — free text, comma-separated (e.g. `painting, oil, 2023`)
   - **Body** — add blocks: images, text, audio, embeds
   - **Attributes** — any extra fields (see scenarios below)
4. **Publish**

Artwork is now live at `/works/<slug>/`

---

### Adding custom Attribute Keys

Before you can add attributes to artworks, define the key once:

**Admin → Snippets → Attribute Keys → Add**

| Name | Type | Example use |
|---|---|---|
| `year` | Number | Year the work was made |
| `status` | String | "ongoing", "completed" |
| `location` | String | Where it was shown |
| `related_work` | Artwork | Links to another artwork (graph edge) |
| `duration` | Number | Duration in minutes |

---

### Adding a Collection

Collections are dynamic — they show artworks that match a set of conditions, always live.

**Admin → Snippets → Collections → Add**

Fields:
- **Name** — display name (e.g. "Ongoing Works")
- **Slug** — URL-safe key, used in the link `/c/<slug>/` (e.g. `ongoing-works`)
- **Description** — optional subtitle shown on the collection page
- **Mode** — `AND` (artwork must match all conditions) or `OR` (match any)
- **Sort by** — `title`, `first_published_at`, or an AttributeKey name (e.g. `year`)
- **Sort dir** — `asc` or `desc`
- **Conditions** — one or more filters (see scenarios below)

Link to a collection anywhere by pasting `/c/<slug>/` into a HomePage link, artist bio, or FlexPage body.

---

### Scenarios

#### Scenario A — All works tagged "painting"

```
Mode: AND
Condition: field=__tag__  op=includes  value=painting
```
URL: `/c/paintings/`

---

#### Scenario B — Works by a specific artist

```
Mode: AND
Condition: field=__artist__  op=eq  value=<artist-slug>
```
(The artist slug is the URL part of their page, e.g. `ana-folau`)

---

#### Scenario C — Ongoing works (status attribute)

First add an AttributeKey: name=`status`, type=String.
Then on each artwork add an attribute: key=`status`, value=`ongoing`.

```
Mode: AND
Condition: field=status  op=eq  value=ongoing
```

---

#### Scenario D — Works made after 2020

First add an AttributeKey: name=`year`, type=Number.
Then set `year` on each artwork.

```
Mode: AND
Condition: field=year  op=gt  value=2020
```

---

#### Scenario E — Works tagged "video" OR "sound"

```
Mode: OR
Condition 1: field=__tag__  op=includes  value=video
Condition 2: field=__tag__  op=includes  value=sound
```

---

#### Scenario F — Works by artist X tagged "installation"

```
Mode: AND
Condition 1: field=__artist__  op=eq      value=<slug>
Condition 2: field=__tag__     op=includes  value=installation
```

---

### Adding a FlexPage

Use FlexPages for any editorial content — a statement page, a project description, a press page.

**Admin → Pages → (choose a parent) → Add child page → Flex Page**

FlexPages can live anywhere in the tree: under Home, under an Artist, standalone.
Their URL is determined by where they sit in the tree.
Body blocks: rich text, images, video embeds, external links.

---

### Useful commands

```bash
# Check for errors without starting the server
python manage.py check

# Open a Django shell
python manage.py shell

# Make new migrations after model changes
python manage.py makemigrations
python manage.py migrate
```

---

## Deploy to test.echulchul.art

The server runs under the `echumggg` user account. Settings are loaded from
`echulchul/settings/production.py` which reads a `.env` file for secrets.

### Required `.env` on the server

```
SECRET_KEY=<long random string>
DB_NAME=<mysql db name>
DB_USER=<mysql user>
DB_PASSWORD=<mysql password>
```

### Deploy steps

```bash
# 1. SSH into the server
ssh echumggg@test.echulchul.art

# 2. Pull latest code
cd ~/echulchul.art
git pull

# 3. Activate virtualenv and install any new deps
source .venv/bin/activate
pip install -r requirements.txt

# 4. Apply migrations
python manage.py migrate --settings=echulchul.settings.production

# 5. Collect static files
python manage.py collectstatic --no-input --settings=echulchul.settings.production

# 6. Restart the app (adjust if using gunicorn/systemd service name)
sudo systemctl restart echulchul
# or: touch ~/test.echulchul.art/tmp/restart.txt  (if using Passenger)
```

### First deploy (new server)

```bash
# Create the superuser on the production DB
python manage.py createsuperuser --settings=echulchul.settings.production
```

Use a strong password here — this is the real admin account.
