# Jordan's Recipes — recipes.jordanherrick.com

A static recipe catalog built from PDF recipe clippings. Each PDF becomes a
structured JSON record, which the build script renders into a browsable site
with search, category filters, per-recipe pages, and a download button for the
original PDF.

## Layout

```
src-pdfs/          original recipe PDFs (source of truth)
data/recipes/      one structured JSON per recipe
scripts/
  extract_image.py extracts the hero photo from a PDF (skips logos/masks)
  build.py         renders the whole site from data/recipes/*.json
site/              generated static site (this is what gets served)
deploy/            Apache vhost config
```

## Add recipes

1. Drop the PDF(s) into `src-pdfs/`.
2. Add a JSON file in `data/recipes/` (see any existing file for the schema).
3. Rebuild:
   ```
   ./.venv/bin/python scripts/build.py
   ```
   The build copies each PDF to `site/pdfs/<slug>.pdf` and auto-extracts a hero
   photo to `site/images/<slug>.jpg` when the PDF contains a usable one.

First-time setup of the local venv:
```
python3 -m venv .venv && ./.venv/bin/pip install PyMuPDF pdfplumber Pillow
```

## Deploy

Same flow as the fitness tracker: commit, push, then pull on the server.

```
git add -A && git commit -m "Update recipes"
git push origin main
ssh pwd "cd /var/www/recipes && git pull --ff-only"
```

The server serves `/var/www/recipes/site` directly — no build step on the
server (the generated site is committed).
