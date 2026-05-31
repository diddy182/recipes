#!/usr/bin/env python3
"""Build the static recipe site from data/recipes/*.json.

For each recipe JSON it:
  - ensures a hero image exists in site/images/ (extracts from the PDF if missing)
  - copies the source PDF to site/pdfs/<slug>.pdf for a clean download URL
  - renders site/recipes/<slug>.html
Then it renders site/index.html (search + category filters + cards), writes the
CSS/JS assets, and the PWA manifest + service worker.

All asset URLs are absolute ("/assets/...", "/app-icons/...") because the Apache
docroot is the site/ folder itself.

Usage: python scripts/build.py
"""
import json
import shutil
import html
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "recipes"
SRC_PDFS = ROOT / "src-pdfs"
SRC_IMAGES = ROOT / "src-images"
SITE = ROOT / "site"
IMAGES = SITE / "images"
PDFS = SITE / "pdfs"
RECIPES_OUT = SITE / "recipes"
ASSETS = SITE / "assets"

SITE_TITLE = "Recipes"
FOOTER_TEXT = f"{SITE_TITLE} · developed by Jordan Herrick"

for d in (IMAGES, PDFS, RECIPES_OUT, ASSETS):
    d.mkdir(parents=True, exist_ok=True)


def e(s):
    return html.escape(str(s or ""))


def load_recipes():
    recipes = []
    for f in sorted(DATA.glob("*.json")):
        with open(f) as fh:
            recipes.append(json.load(fh))
    return recipes


def ensure_assets(recipe):
    """Make sure the hero image and downloadable PDF exist for a recipe."""
    slug = recipe["slug"]
    src_pdf = SRC_PDFS / recipe["pdf"] if recipe.get("pdf") else None
    has_pdf = False
    if src_pdf and src_pdf.exists():
        shutil.copyfile(src_pdf, PDFS / f"{slug}.pdf")
        has_pdf = True
    img_name = recipe.get("image")
    has_img = False
    if img_name:
        src_img = SRC_IMAGES / img_name
        if src_img.exists():
            shutil.copyfile(src_img, IMAGES / img_name)
            has_img = True
        elif (IMAGES / img_name).exists():
            has_img = True
    if not has_img and src_pdf and src_pdf.exists():
        try:
            import sys
            sys.path.insert(0, str(ROOT / "scripts"))
            from extract_image import extract_hero
            out = IMAGES / f"{slug}.jpg"
            if extract_hero(str(src_pdf), str(out)):
                recipe["image"] = f"{slug}.jpg"
                has_img = True
        except Exception as ex:
            print(f"  ! image extract failed for {slug}: {ex}")
    return has_pdf, has_img


def ingredient_text(recipe):
    """Flatten all ingredient lines into one lowercase search string."""
    parts = []
    for group in recipe.get("ingredients", []):
        if group.get("heading"):
            parts.append(group["heading"])
        parts.extend(group.get("items", []))
    return " ".join(parts).lower()


def meta_cells(recipe):
    rows = [
        ("Yield", recipe.get("yield")),
        ("Prep", recipe.get("prep_time")),
        ("Cook", recipe.get("cook_time")),
        ("Total", recipe.get("total_time")),
        ("Calories", recipe.get("calories")),
    ]
    cells = "".join(
        f'<div class="meta-item"><span class="meta-label">{e(l)}</span>'
        f'<span class="meta-value">{e(v)}</span></div>'
        for l, v in rows if v
    )
    return f'<div class="meta">{cells}</div>' if cells else ""


def render_ingredients(recipe):
    out = []
    for group in recipe.get("ingredients", []):
        if group.get("heading"):
            out.append(f'<h3 class="ing-heading">{e(group["heading"])}</h3>')
        out.append('<ul class="ingredients">')
        for item in group.get("items", []):
            out.append(f"<li>{e(item)}</li>")
        out.append("</ul>")
    return "\n".join(out)


def render_instructions(recipe):
    steps = recipe.get("instructions", [])
    if not steps:
        return ""
    lis = "\n".join(f"<li>{e(s)}</li>" for s in steps)
    return f'<ol class="instructions">{lis}</ol>'


def render_notes(recipe):
    notes = recipe.get("notes", [])
    if not notes:
        return ""
    items = []
    for n in notes:
        label = f'<strong>{e(n["label"])}:</strong> ' if n.get("label") else ""
        items.append(f"<li>{label}{e(n.get('text',''))}</li>")
    return ('<section class="notes"><h2>Notes</h2>'
            f'<ul class="notes-list">{"".join(items)}</ul></section>')


def render_nutrition(recipe):
    n = recipe.get("nutrition")
    if not n:
        return ""
    return (f'<section class="nutrition"><h2>Nutrition</h2>'
            f'<p>{e(n)}</p></section>')


def render_source(recipe):
    """Bottom-of-page provenance: contributor (who shared it) + original source."""
    lines = []
    contributor = recipe.get("contributor")
    if contributor:
        lines.append(f'<p class="source">From the kitchen of <strong>{e(contributor)}</strong></p>')
    name = recipe.get("source_name")
    url = recipe.get("source_url")
    if url:
        label = name or "original source"
        lines.append('<p class="source">Recipe from '
                     f'<a href="{e(url)}" target="_blank" rel="noopener">{e(label)}</a></p>')
    elif name:
        lines.append(f'<p class="source">Recipe from {e(name)}</p>')
    return "\n".join(lines)


def _valid_ratings(recipe):
    return [r for r in (recipe.get("ratings") or [])
            if isinstance(r.get("score"), (int, float))]


def avg_rating(recipe):
    rs = _valid_ratings(recipe)
    return sum(r["score"] for r in rs) / len(rs) if rs else None


def fmt_rating(v):
    """One decimal, but drop it for whole numbers: 8.0 -> '8', 7.5 -> '7.5'."""
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:.1f}"


def render_ratings(recipe):
    rs = _valid_ratings(recipe)
    if not rs:
        return ""
    avg = sum(r["score"] for r in rs) / len(rs)
    people = "".join(
        f'<li><span class="r-name">{e(r["name"])}</span>'
        f'<span class="r-score">{fmt_rating(r["score"])}</span></li>'
        for r in rs
    )
    return ('<div class="ratings">'
            f'<div class="ratings-score"><span class="ratings-avg">{fmt_rating(avg)}</span>'
            '<span class="ratings-out">/10</span></div>'
            f'<ul class="ratings-people">{people}</ul></div>')


HEAD_META = """<meta name="theme-color" content="#1a1a1a">
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" href="/app-icons/icon-32.png">
<link rel="apple-touch-icon" href="/app-icons/icon-180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Recipes">"""

SW_REG = """<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js'));
}
</script>"""


def page_shell(title, body, description=""):
    desc = f'<meta name="description" content="{e(description)}">' if description else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
{desc}
{HEAD_META}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Karla:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css?v={ASSET_VER}">
</head>
<body>
{body}
{SW_REG}
</body>
</html>"""


def render_recipe_page(recipe):
    slug = recipe["slug"]
    img = recipe.get("image")
    img_exists = bool(img) and (IMAGES / img).exists()
    hero = (f'<figure class="hero"><img src="/images/{e(img)}" alt="{e(recipe["title"])}"></figure>'
            if img_exists else "")
    top_class = "recipe-top" if img_exists else "recipe-top no-hero"
    desc = f'<p class="recipe-desc">{e(recipe["description"])}</p>' if recipe.get("description") else ""
    contributor = recipe.get("contributor")
    eyebrow_bits = [recipe.get("category") or "Recipe"]
    if contributor:
        eyebrow_bits.append(f"from {contributor}")
    eyebrow = '<span>' + '</span><span>'.join(e(b) for b in eyebrow_bits) + '</span>'
    body = f"""<header class="site-header">
<a class="brand" href="/index.html">{e(SITE_TITLE)}</a>
<a class="back" href="/index.html">All recipes</a>
</header>
<main class="recipe">
<div class="{top_class}">
<div class="recipe-head">
<p class="eyebrow">{eyebrow}</p>
<h1>{e(recipe["title"])}</h1>
{desc}
{meta_cells(recipe)}
{render_ratings(recipe)}
<a class="download-btn" href="/pdfs/{e(slug)}.pdf" download>Download PDF</a>
</div>
{hero}
</div>
<div class="recipe-body">
<section class="ingredients-section">
<h2>Ingredients</h2>
{render_ingredients(recipe)}
</section>
<section class="instructions-section">
<h2>Method</h2>
{render_instructions(recipe)}
</section>
</div>
{render_notes(recipe)}
{render_nutrition(recipe)}
<div class="provenance">{render_source(recipe)}</div>
</main>
<footer class="site-footer">{e(FOOTER_TEXT)}</footer>"""
    return page_shell(f'{recipe["title"]} — {SITE_TITLE}', body,
                      description=recipe.get("description", ""))


def render_card(recipe):
    slug = recipe["slug"]
    img = recipe.get("image")
    img_exists = bool(img) and (IMAGES / img).exists()
    thumb = (f'<img loading="lazy" src="/images/{e(img)}" alt="{e(recipe["title"])}">'
             if img_exists else '<div class="noimg"></div>')
    rating = avg_rating(recipe)
    badge = (f'<span class="card-rating">{fmt_rating(rating)}<span class="cr-out">/10</span></span>'
             if rating is not None else "")
    contributor = recipe.get("contributor")
    cat = recipe.get("category") or ""
    meta_bits = [b for b in (cat, f"from {contributor}" if contributor else "") if b]
    meta_html = "".join(f"<span>{e(b)}</span>" for b in meta_bits)
    tags = " ".join((recipe.get("tags") or []) + [cat, contributor or ""])
    haystack = " ".join([
        recipe["title"].lower(), tags.lower(),
        ingredient_text(recipe),
    ])
    return f"""<a class="card" href="/recipes/{e(slug)}.html"
  data-category="{e(cat.lower())}"
  data-search="{e(haystack)}">
  <div class="card-img">{badge}{thumb}</div>
  <div class="card-body">
    <p class="card-meta">{meta_html}</p>
    <h2>{e(recipe['title'])}</h2>
  </div>
</a>"""


def render_index(recipes):
    cats = sorted({r.get("category") for r in recipes if r.get("category")})
    chips = '<button class="chip active" data-cat="all">All</button>'
    chips += "".join(
        f'<button class="chip" data-cat="{e(c.lower())}">{e(c)}</button>' for c in cats
    )
    cards = "\n".join(render_card(r) for r in
                      sorted(recipes, key=lambda r: r["title"].lower()))
    count = len(recipes)
    body = f"""<header class="site-header home">
<a class="brand" href="/index.html">{e(SITE_TITLE)}</a>
</header>
<main class="home-main">
<section class="masthead">
<h1>{e(SITE_TITLE)}</h1>
<p class="tagline">A collection of {count} recipe{'s' if count != 1 else ''} — clipped, cooked, and kept.</p>
<input id="search" type="search" placeholder="Search by name, ingredient, or tag…" autocomplete="off">
<div class="chips">{chips}</div>
</section>
<p id="empty" class="empty" hidden>No recipes match your search.</p>
<section class="grid" id="grid">
{cards}
</section>
</main>
<footer class="site-footer">{e(FOOTER_TEXT)}</footer>
<script src="/assets/app.js?v={ASSET_VER}"></script>"""
    return page_shell(SITE_TITLE, body,
                      description=f"A personal collection of {count} recipes.")


CSS = r""":root{
  --dark:#1a1a1a; --text2:#3a3a3a; --muted:#6e6e6e; --muted2:#9a9a9a;
  --border:#ebe8e2; --border-soft:#f3f1ec; --gray:#fafaf8; --light:#fff;
  --serif:'EB Garamond',Georgia,serif;
  --sans:'Karla',system-ui,-apple-system,sans-serif;
}
*{box-sizing:border-box}
html{font-size:16px}
body{margin:0;background:var(--light);color:var(--dark);
  font-family:var(--serif);font-size:1.125rem;line-height:1.6;
  -webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
h1,h2,h3{font-family:var(--serif);font-weight:500;line-height:1.15;
  letter-spacing:-.01em;margin:0}

/* Header / footer */
.site-header{display:flex;align-items:center;justify-content:space-between;
  max-width:1140px;margin:0 auto;padding:28px 32px;
  border-bottom:1px solid var(--border)}
.brand{font-family:var(--serif);font-weight:500;font-size:1.5rem;letter-spacing:-.01em}
.back{font-family:var(--sans);font-weight:500;font-size:.8125rem;
  text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
  border-bottom:1px solid transparent;padding-bottom:1px;transition:.15s}
.back:hover{color:var(--dark);border-bottom-color:var(--dark)}
.site-footer{font-family:var(--sans);text-align:center;color:var(--muted2);
  padding:56px 0 72px;font-size:.8125rem;letter-spacing:.08em;text-transform:uppercase}

/* Home masthead */
.home-main{max-width:1140px;margin:0 auto;padding:0 32px}
.masthead{text-align:center;padding:64px 0 40px;border-bottom:1px solid var(--border)}
.masthead h1{font-size:clamp(2.4rem,6vw,3.6rem)}
.tagline{font-style:italic;color:var(--muted);margin:.6rem 0 2rem;font-size:1.1875rem}
#search{width:100%;max-width:520px;font-family:var(--serif);font-size:1.0625rem;
  padding:13px 18px;border:1px solid var(--border);background:var(--light);
  border-radius:0;outline:none;transition:border-color .15s}
#search:focus{border-color:var(--dark)}
.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:22px}
.chip{font-family:var(--sans);font-size:.8125rem;font-weight:500;
  color:var(--text2);background:var(--gray);border:1px solid var(--border-soft);
  padding:7px 15px;border-radius:999px;cursor:pointer;transition:.15s}
.chip:hover{background:var(--light);border-color:var(--border);color:var(--dark)}
.chip.active{background:var(--dark);border-color:var(--dark);color:var(--light)}

/* Grid of recipe cards */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));
  gap:36px 28px;padding:48px 0 24px}
.card{display:flex;flex-direction:column}
.card-img{position:relative;aspect-ratio:1/1;background:var(--gray);overflow:hidden}
.card-rating{position:absolute;top:9px;right:9px;z-index:1;
  font-family:var(--sans);font-weight:700;font-size:.8125rem;line-height:1;
  background:rgba(26,26,26,.82);color:#fff;padding:5px 9px;border-radius:999px;
  letter-spacing:.01em;-webkit-backdrop-filter:blur(2px);backdrop-filter:blur(2px)}
.card-rating .cr-out{font-weight:500;opacity:.7;font-size:.6875rem}
.card-img img{width:100%;height:100%;object-fit:cover;display:block;
  transition:transform .4s ease}
.card:hover .card-img img{transform:scale(1.04)}
.noimg{width:100%;height:100%;background:var(--border-soft)}
.card-body{padding:14px 2px 0}
.card-meta{font-family:var(--sans);font-size:.6875rem;font-weight:500;
  text-transform:uppercase;letter-spacing:.07em;color:var(--muted);
  margin:0 0 5px;display:flex;flex-wrap:wrap;gap:0 6px}
.card-meta > * + *::before{content:'·';margin-right:6px;color:var(--muted2)}
.card-body h2{font-size:1.375rem;font-weight:500}
.empty{font-family:var(--sans);text-align:center;color:var(--muted);padding:64px 0}

/* Recipe page */
.recipe{max-width:880px;margin:0 auto;padding:48px 32px 0}
.recipe-top{display:grid;grid-template-columns:1fr 300px;gap:44px;
  align-items:start;margin-bottom:8px}
.recipe-top.no-hero{grid-template-columns:1fr;max-width:680px}
.eyebrow{font-family:var(--sans);font-size:.75rem;font-weight:600;
  text-transform:uppercase;letter-spacing:.1em;color:var(--muted);
  margin:0 0 12px;display:flex;flex-wrap:wrap;gap:0 6px}
.eyebrow > * + *::before{content:'·';margin-right:6px;color:var(--muted2)}
.recipe-head h1{font-size:clamp(2rem,4.5vw,2.9rem);margin-bottom:.6rem}
.recipe-desc{font-style:italic;color:var(--muted);margin:0 0 22px;font-size:1.1875rem}
.hero{margin:0}
.hero img{width:100%;aspect-ratio:1/1;object-fit:cover;display:block;background:var(--gray)}
.meta{display:flex;flex-wrap:wrap;gap:26px;margin:0 0 26px;padding:18px 0;
  border-top:1px solid var(--border);border-bottom:1px solid var(--border)}
.meta-item{display:flex;flex-direction:column;gap:3px}
.meta-label{font-family:var(--sans);font-size:.6875rem;font-weight:600;
  text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.meta-value{font-size:1.0625rem}
.download-btn{display:inline-block;font-family:var(--sans);font-weight:600;
  font-size:.8125rem;text-transform:uppercase;letter-spacing:.08em;
  background:var(--dark);color:var(--light);padding:13px 26px;
  border-radius:0;transition:background .15s}
.download-btn:hover{background:var(--text2)}
.ratings{display:flex;align-items:center;gap:28px;flex-wrap:wrap;
  margin:0 0 26px;padding:18px 0;
  border-top:1px solid var(--border);border-bottom:1px solid var(--border)}
.ratings-score{display:flex;align-items:baseline;gap:2px}
.ratings-avg{font-family:var(--sans);font-weight:700;font-size:2.1rem;line-height:1}
.ratings-out{font-family:var(--sans);font-size:.95rem;color:var(--muted)}
.ratings-people{list-style:none;margin:0;padding:0;display:flex;gap:24px;flex-wrap:wrap}
.ratings-people li{display:flex;flex-direction:column;gap:3px}
.r-name{font-family:var(--sans);font-size:.6875rem;font-weight:600;
  text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.r-score{font-family:var(--sans);font-size:1.0625rem;font-weight:600}

.recipe-body{display:grid;grid-template-columns:1fr 1.5fr;gap:52px;
  margin-top:40px;padding-top:40px;border-top:1px solid var(--border)}
.recipe-body h2{font-size:1.625rem;margin-bottom:18px}
.ingredients{list-style:none;padding:0;margin:0}
.ingredients li{padding:9px 0;border-bottom:1px solid var(--border-soft);line-height:1.45}
.ing-heading{font-size:1.125rem;font-weight:600;margin:20px 0 6px}
.instructions{padding:0;list-style:none;counter-reset:step;margin:0}
.instructions li{position:relative;padding:0 0 22px 48px;counter-increment:step}
.instructions li:before{content:counter(step,decimal-leading-zero);
  position:absolute;left:0;top:1px;font-family:var(--sans);font-weight:700;
  font-size:.875rem;color:var(--muted2);letter-spacing:.02em}

.notes{max-width:880px;margin:40px auto 0;padding:28px 32px;background:var(--gray);
  border:1px solid var(--border-soft)}
.notes h2{font-size:1.375rem;margin-bottom:12px}
.notes-list{margin:0;padding-left:20px}
.notes-list li{margin-bottom:10px;line-height:1.5}
.nutrition{max-width:880px;margin:40px auto 0;padding-top:24px;border-top:1px solid var(--border)}
.nutrition h2{font-size:1.25rem;margin-bottom:8px}
.nutrition p{color:var(--muted);font-size:1rem;margin:0}
.provenance{max-width:880px;margin:36px auto 0;padding-top:24px;border-top:1px solid var(--border)}
.source{font-family:var(--sans);color:var(--muted);font-size:.9375rem;margin:0 0 6px}
.source strong{color:var(--text2);font-weight:600}
.source a{color:var(--dark);border-bottom:1px solid var(--border);padding-bottom:1px}
.source a:hover{border-bottom-color:var(--dark)}

@media(max-width:768px){
  .recipe-top{grid-template-columns:1fr;gap:28px}
  .recipe-top .hero{order:-1}
  .hero img{aspect-ratio:4/3}
  .recipe-body{grid-template-columns:1fr;gap:36px}
}
@media(max-width:600px){
  .site-header{padding:22px 22px}
  .home-main{padding:0 22px}
  .recipe{padding:36px 22px 0}
  .masthead{padding:44px 0 32px}
  .grid{gap:30px 20px;padding:36px 0 16px}
}
"""

JS = r"""const search = document.getElementById('search');
const grid = document.getElementById('grid');
const cards = Array.from(grid.querySelectorAll('.card'));
const chips = Array.from(document.querySelectorAll('.chip'));
const empty = document.getElementById('empty');
let activeCat = 'all';

function apply(){
  const q = search.value.trim().toLowerCase();
  let shown = 0;
  cards.forEach(card => {
    const matchText = !q || card.dataset.search.includes(q);
    const matchCat = activeCat === 'all' || card.dataset.category === activeCat;
    const show = matchText && matchCat;
    card.style.display = show ? '' : 'none';
    if (show) shown++;
  });
  empty.hidden = shown !== 0;
}

search.addEventListener('input', apply);
chips.forEach(chip => chip.addEventListener('click', () => {
  chips.forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  activeCat = chip.dataset.cat;
  apply();
}));
"""

MANIFEST = {
    "name": "Jordan's Recipes",
    "short_name": "Recipes",
    "description": "A personal collection of recipes.",
    "start_url": "/index.html",
    "scope": "/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#1a1a1a",
    "icons": [
        {"src": "/app-icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/app-icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
        {"src": "/app-icons/icon-maskable-512.png", "sizes": "512x512",
         "type": "image/png", "purpose": "maskable"},
    ],
}

SW = r"""/* Jordan's Recipes — service worker */
const CACHE_VERSION = 'recipes-__ASSET_VER__';
const SHELL = [
  '/',
  '/index.html',
  '/assets/style.css?v=__ASSET_VER__',
  '/assets/app.js?v=__ASSET_VER__',
  '/manifest.json',
  '/app-icons/icon-192.png',
  '/app-icons/icon-512.png',
  '/app-icons/icon-180.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // PDFs are large — let them hit the network directly.
  if (url.pathname.startsWith('/pdfs/')) return;

  event.respondWith(
    fetch(req)
      .then((resp) => {
        if (resp && resp.ok && resp.type === 'basic') {
          const copy = resp.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(req, copy));
        }
        return resp;
      })
      .catch(() => caches.match(req).then((hit) => hit || caches.match('/index.html')))
  );
});
"""


# Content hash of the CSS/JS — appended to asset URLs (?v=…) so a new deploy
# always serves under a fresh URL, defeating Cloudflare/browser caching of stale assets.
ASSET_VER = hashlib.md5((CSS + JS).encode("utf-8")).hexdigest()[:8]


def main():
    recipes = load_recipes()
    print(f"Building {len(recipes)} recipe(s)…")
    for r in recipes:
        ensure_assets(r)
        out = RECIPES_OUT / f"{r['slug']}.html"
        out.write_text(render_recipe_page(r), encoding="utf-8")
        print(f"  ✓ {r['slug']}")
    (SITE / "index.html").write_text(render_index(recipes), encoding="utf-8")
    (ASSETS / "style.css").write_text(CSS, encoding="utf-8")
    (ASSETS / "app.js").write_text(JS, encoding="utf-8")
    (SITE / "manifest.json").write_text(json.dumps(MANIFEST, indent=2), encoding="utf-8")
    (SITE / "sw.js").write_text(SW.replace("__ASSET_VER__", ASSET_VER), encoding="utf-8")
    print("Done. Open site/index.html")


if __name__ == "__main__":
    main()
