#!/usr/bin/env python3
"""Build the static recipe site from data/recipes/*.json.

For each recipe JSON it:
  - ensures a hero image exists in site/images/ (extracts from the PDF if missing)
  - copies the source PDF to site/pdfs/<slug>.pdf for a clean download URL
  - renders site/recipes/<slug>.html
Then it renders site/index.html (search + category filters + cards) and writes
the CSS/JS assets.

Usage: python scripts/build.py
"""
import json
import shutil
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "recipes"
SRC_PDFS = ROOT / "src-pdfs"
SITE = ROOT / "site"
IMAGES = SITE / "images"
PDFS = SITE / "pdfs"
RECIPES_OUT = SITE / "recipes"
ASSETS = SITE / "assets"

SITE_TITLE = "Jordan's Recipes"

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
    # PDF: copy source -> site/pdfs/<slug>.pdf
    src_pdf = SRC_PDFS / recipe["pdf"] if recipe.get("pdf") else None
    has_pdf = False
    if src_pdf and src_pdf.exists():
        shutil.copyfile(src_pdf, PDFS / f"{slug}.pdf")
        has_pdf = True
    # Image: extract if referenced but missing
    img_name = recipe.get("image")
    has_img = bool(img_name) and (IMAGES / img_name).exists()
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


META_ROW = """<div class="meta">{cells}</div>"""


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
    return META_ROW.format(cells=cells) if cells else ""


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
    name = recipe.get("source_name")
    url = recipe.get("source_url")
    if url:
        label = name or "original source"
        return (f'<p class="source">Recipe from '
                f'<a href="{e(url)}" target="_blank" rel="noopener">{e(label)}</a></p>')
    if name:
        return f'<p class="source">Recipe from {e(name)}</p>'
    return ""


def page_shell(title, body, rel="../"):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{rel}assets/style.css">
</head>
<body>
{body}
</body>
</html>"""


def render_recipe_page(recipe):
    slug = recipe["slug"]
    img = recipe.get("image")
    img_exists = bool(img) and (IMAGES / img).exists()
    hero = (f'<img class="hero" src="../images/{e(img)}" alt="{e(recipe["title"])}">'
            if img_exists else "")
    top_class = "recipe-top" if img_exists else "recipe-top no-hero"
    source = render_source(recipe)
    desc = f'<p class="recipe-desc">{e(recipe["description"])}</p>' if recipe.get("description") else ""
    body = f"""<header class="site-header">
<a class="brand" href="../index.html">{e(SITE_TITLE)}</a>
<a class="back" href="../index.html">&larr; All recipes</a>
</header>
<main class="recipe">
<div class="{top_class}">
<div class="recipe-head">
<p class="eyebrow">{e(recipe.get("category") or "Recipe")}</p>
<h1>{e(recipe["title"])}</h1>
{desc}
{meta_cells(recipe)}
<a class="download-btn" href="../pdfs/{e(slug)}.pdf" download>Download PDF</a>
</div>
{hero}
</div>
<div class="recipe-body">
<section class="ingredients-section">
<h2>Ingredients</h2>
{render_ingredients(recipe)}
</section>
<section class="instructions-section">
<h2>Instructions</h2>
{render_instructions(recipe)}
</section>
</div>
{render_notes(recipe)}
{render_nutrition(recipe)}
{source}
</main>
<footer class="site-footer">{e(SITE_TITLE)}</footer>"""
    return page_shell(f'{recipe["title"]} — {SITE_TITLE}', body, rel="../")


def render_card(recipe):
    slug = recipe["slug"]
    img = recipe.get("image")
    img_exists = bool(img) and (IMAGES / img).exists()
    thumb = (f'<img loading="lazy" src="images/{e(img)}" alt="{e(recipe["title"])}">'
             if img_exists else '<div class="noimg">🍴</div>')
    time = recipe.get("total_time") or recipe.get("cook_time") or ""
    time_html = f'<span class="card-time">{e(time)}</span>' if time else ""
    tags = " ".join((recipe.get("tags") or []) + [recipe.get("category") or ""])
    return f"""<a class="card" href="recipes/{e(slug)}.html"
  data-title="{e(recipe['title'].lower())}"
  data-category="{e((recipe.get('category') or '').lower())}"
  data-tags="{e(tags.lower())}">
  <div class="card-img">{thumb}</div>
  <div class="card-body">
    <span class="card-cat">{e(recipe.get('category') or '')}</span>
    <h2>{e(recipe['title'])}</h2>
    {time_html}
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
<a class="brand" href="index.html">{e(SITE_TITLE)}</a>
</header>
<main class="home-main">
<section class="hero-band">
<h1>{e(SITE_TITLE)}</h1>
<p class="tagline">{count} recipe{'s' if count != 1 else ''}, all in one place.</p>
<input id="search" type="search" placeholder="Search recipes, ingredients, tags…" autocomplete="off">
<div class="chips">{chips}</div>
</section>
<div id="empty" class="empty" hidden>No recipes match your search.</div>
<section class="grid" id="grid">
{cards}
</section>
</main>
<footer class="site-footer">{e(SITE_TITLE)}</footer>
<script src="assets/app.js"></script>"""
    return page_shell(SITE_TITLE, body, rel="")


CSS = r""":root{
  --bg:#faf7f2; --card:#fff; --ink:#2c2620; --muted:#8a7f70;
  --accent:#c2410c; --accent-soft:#fde7d8; --line:#ece5da; --shadow:0 1px 3px rgba(60,40,20,.08),0 8px 24px rgba(60,40,20,.06);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:'Inter',system-ui,sans-serif;line-height:1.6}
a{color:inherit;text-decoration:none}
h1,h2,h3{font-family:'Fraunces',Georgia,serif;font-weight:600;line-height:1.15;margin:0}

.site-header{display:flex;align-items:center;justify-content:space-between;padding:18px 24px;border-bottom:1px solid var(--line);background:rgba(250,247,242,.85);backdrop-filter:blur(8px);position:sticky;top:0;z-index:10}
.brand{font-family:'Fraunces',serif;font-weight:700;font-size:1.25rem;color:var(--accent)}
.back{color:var(--muted);font-size:.92rem}
.site-footer{text-align:center;color:var(--muted);padding:48px 0 64px;font-size:.85rem}

/* Home */
.home-main{max-width:1120px;margin:0 auto;padding:0 24px}
.hero-band{text-align:center;padding:56px 0 36px}
.hero-band h1{font-size:clamp(2.2rem,5vw,3.4rem)}
.tagline{color:var(--muted);margin:.5rem 0 1.8rem}
#search{width:100%;max-width:560px;padding:14px 18px;font-size:1rem;border:1px solid var(--line);border-radius:14px;background:#fff;box-shadow:var(--shadow);outline:none}
#search:focus{border-color:var(--accent)}
.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:20px}
.chip{border:1px solid var(--line);background:#fff;color:var(--muted);padding:7px 16px;border-radius:999px;font-size:.88rem;cursor:pointer;font-family:inherit;transition:.15s}
.chip:hover{border-color:var(--accent);color:var(--accent)}
.chip.active{background:var(--accent);border-color:var(--accent);color:#fff}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(248px,1fr));gap:22px;padding-bottom:24px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:var(--shadow);transition:transform .18s,box-shadow .18s;display:flex;flex-direction:column}
.card:hover{transform:translateY(-4px);box-shadow:0 6px 14px rgba(60,40,20,.12),0 18px 40px rgba(60,40,20,.10)}
.card-img{aspect-ratio:4/3;background:var(--accent-soft);overflow:hidden}
.card-img img{width:100%;height:100%;object-fit:cover;display:block}
.noimg{display:flex;align-items:center;justify-content:center;height:100%;font-size:2.4rem;opacity:.5}
.card-body{padding:14px 16px 18px}
.card-cat{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--accent);font-weight:600}
.card-body h2{font-size:1.12rem;margin:4px 0 6px}
.card-time{font-size:.85rem;color:var(--muted)}
.empty{text-align:center;color:var(--muted);padding:48px 0}

/* Recipe page */
.recipe{max-width:860px;margin:0 auto;padding:32px 24px 0}
.recipe-top{display:grid;grid-template-columns:1fr 320px;gap:32px;align-items:start;margin-bottom:8px}
.eyebrow{font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;color:var(--accent);font-weight:600;margin:0 0 6px}
.recipe-head h1{font-size:clamp(1.9rem,4vw,2.6rem);margin-bottom:.5rem}
.recipe-desc{color:var(--muted);margin:0 0 18px}
.hero{width:100%;border-radius:16px;box-shadow:var(--shadow);aspect-ratio:1/1;object-fit:cover}
.meta{display:flex;flex-wrap:wrap;gap:18px;margin:0 0 20px;padding:14px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.meta-item{display:flex;flex-direction:column}
.meta-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.meta-value{font-weight:600}
.download-btn{display:inline-block;background:var(--accent);color:#fff;padding:12px 22px;border-radius:12px;font-weight:600;box-shadow:var(--shadow);transition:.15s}
.download-btn:hover{background:#9a330a}

.recipe-body{display:grid;grid-template-columns:1fr 1.4fr;gap:40px;margin-top:28px}
.recipe-body h2{font-size:1.4rem;margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid var(--accent-soft)}
.ingredients{list-style:none;padding:0;margin:0}
.ingredients li{padding:7px 0 7px 26px;position:relative;border-bottom:1px dashed var(--line)}
.ingredients li:before{content:"";position:absolute;left:4px;top:15px;width:7px;height:7px;border-radius:50%;background:var(--accent)}
.ing-heading{font-size:1rem;margin:14px 0 6px}
.instructions{padding-left:0;list-style:none;counter-reset:step;margin:0}
.instructions li{position:relative;padding:0 0 18px 46px;counter-increment:step}
.instructions li:before{content:counter(step);position:absolute;left:0;top:0;width:30px;height:30px;background:var(--accent-soft);color:var(--accent);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.9rem}
.recipe-top.no-hero{grid-template-columns:1fr}
.card-img .noimg{background:linear-gradient(135deg,var(--accent-soft),#fff)}
.notes{max-width:860px;margin:24px auto 0;padding:24px;background:var(--accent-soft);border-radius:16px}
.notes h2{font-size:1.3rem;margin-bottom:10px}
.notes-list{margin:0;padding-left:20px}
.notes-list li{margin-bottom:8px}
.nutrition{max-width:860px;margin:24px auto 0;padding-top:18px;border-top:1px solid var(--line)}
.nutrition h2{font-size:1.15rem;margin-bottom:8px}
.nutrition p{color:var(--muted);font-size:.88rem;margin:0}
.source{max-width:860px;margin:24px auto 0;color:var(--muted);font-size:.9rem}
.source a{color:var(--accent);text-decoration:underline}

@media(max-width:720px){
  .recipe-top{grid-template-columns:1fr}
  .hero{max-width:320px}
  .recipe-body{grid-template-columns:1fr;gap:28px}
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
    const hay = card.dataset.title + ' ' + card.dataset.tags;
    const matchText = !q || hay.includes(q);
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
    print(f"Done. Open site/index.html")


if __name__ == "__main__":
    main()
