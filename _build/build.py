"""Generic Bachat static site generator.

python3 _build/match.py   # raw data -> _data/matched.json
python3 _build/build.py   # matched.json + store list -> HTML pages, JSON search index, sitemap
"""
import json, os, re, html, statistics, datetime, shutil, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "_data", "raw")
BASE = ""
SITE = "https://chinmaya2310.github.io" + BASE
PORTFOLIO = "https://chinmaya2310.github.io/portfolio/"
GSC = "30sAjotF1Gglg-_EVpD2LCbYcUsk-VZQFdx3HA7s4Ac"
GA = "G-G5MBDW1E1F"
NAME = "Generic Bachat"
TODAY = datetime.date.today().isoformat()
DATA_DATE = "17 November 2026"
N_BRAND_PAGES = 2000
E = html.escape

# ------------------------------------------------------------------ helpers
def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)

def rs(v):
    return f"₹{v:,.0f}" if v >= 100 else f"₹{v:.2f}"

def strength_label(st):
    m = re.match(r"([\d.]+)(mg|iu|%)", st)
    v, u = float(m.group(1)), m.group(2)
    if u == "mg" and v < 1:
        return f"{v * 1000:g} mcg"
    if u == "mg" and v >= 1000 and v % 1000 == 0:
        return f"{v / 1000:g} g"
    return f"{v:g} {'IU' if u == 'iu' else u}"

def salt_title(s):
    return " ".join(w.capitalize() for w in s.split())

def salt_label(comps, release, form):
    parts = [f"{salt_title(s)} {strength_label(st)}" for s, st in comps]
    lab = " + ".join(parts)
    return lab + (" (SR)" if release == "mr" else "")

def short_mfr(m):
    m = re.sub(r"\b(Pvt\.?|Private|Ltd\.?|Limited|India|Inc\.?|Co\.?)\b", "", m)
    m = m.replace("Pharmaceuticals", "Pharma").replace("Laboratories", "Labs")
    return re.sub(r"\s+", " ", m).strip(" ,.-")

def write(rel, text):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)

def pct(b, g):
    v = 100 * (b - g) / b
    return min(99, int(v)) if v > 0 else round(v)

# ------------------------------------------------------------------ layout
def head(title, desc, path, jsonld=(), extra_head="", robots="index, follow"):
    url = SITE + path
    gsc = f'\n  <meta name="google-site-verification" content="{GSC}">' if path == "/" else ""
    ld = "".join(f'\n  <script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in jsonld)
    return f"""<!DOCTYPE html>
<html lang="en-IN" data-base="{BASE}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{E(title)}</title>
  <meta name="description" content="{E(desc)}">
  <meta name="robots" content="{robots}">{gsc}
  <link rel="canonical" href="{url}">
  <link rel="icon" href="{BASE}/assets/favicon.svg" type="image/svg+xml">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{NAME}">
  <meta property="og:locale" content="en_IN">
  <meta property="og:title" content="{E(title)}">
  <meta property="og:description" content="{E(desc)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SITE}/assets/og.png">
  <meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">{ld}
  <link rel="stylesheet" href="{BASE}/assets/style.css">{extra_head}
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA}',{{content_group:'{content_group(path)}'}});</script>
  <script src="{BASE}/assets/app.js" defer></script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="wrap">
  <a class="logo" href="{BASE}/">Generic Bachat<span>Jan Aushadhi price finder</span></a>
  <nav aria-label="Main"><a href="{BASE}/">Search</a><a href="{BASE}/stores/">Kendras</a><a href="{BASE}/medicines/">Medicines</a><a href="{BASE}/about/">About</a></nav>
</div></header>
"""

def content_group(path):
    for k in ("medicine", "brand", "stores", "about", "medicines"):
        if path.startswith(f"/{k}/"): return k
    return "home"

FOOT = f"""
<footer class="site-footer"><div class="wrap">
  <p>This site only compares prices. It isn't medical advice, and it isn't connected to PMBI or the Government of India. Talk to your doctor or pharmacist before you switch any medicine.</p>
  <p>Jan Aushadhi prices and Kendra list from janaushadhi.gov.in. Brand prices from a public dataset, so some will be out of date.
  <a href="{BASE}/about/">How this works</a> · Made by <a href="{PORTFOLIO}?utm_source=generic_bachat&utm_medium=referral&utm_campaign=footer" data-track="footer_author">Chinmaya Nayak</a></p>
</div></footer>
</body>
</html>
"""

def crumbs(items):
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + p} for i, (n, p) in enumerate(items)]}
    h = " › ".join(f'<a href="{BASE}{p}">{E(n)}</a>' if i < len(items) - 1 else f'<span aria-current="page">{E(n)}</span>'
                   for i, (n, p) in enumerate(items))
    return ld, f'<nav class="crumbs" aria-label="Breadcrumb">{h}</nav>'

def faq_block(qas):
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", a)}} for q, a in qas]}
    h = "".join(f"<h3>{E(q)}</h3><p>{a}</p>" for q, a in qas)
    return ld, h

# ------------------------------------------------------------------ data
matched = json.load(open(os.path.join(ROOT, "_data", "matched.json")))
products = json.load(open(os.path.join(RAW, "products.json")))["responseBody"]["newProductResponsesList"]
kendras = json.load(open(os.path.join(RAW, "kendras.json")))["responseBody"]["addKendraResponseList"]

gens = []
used_slugs = set()
for g in matched:
    lab = salt_label(g["comps"], g["release"], g["form"])
    base = slugify(lab.replace("(SR)", "sr") + " " + g["form"])
    slug = base
    k = 2
    while slug in used_slugs:
        slug = f"{base}-{k}"; k += 1
    used_slugs.add(slug)
    # one entry per brand name (cheapest pack per unit kept)
    by_name = {}
    for b in g["brands"]:
        key = b["name"].lower()
        if key not in by_name or b["rank"] < by_name[key]["rank"]:
            by_name[key] = b
    brands = sorted(by_name.values(), key=lambda b: b["rank"])
    gens.append({**g, "slug": slug, "label": lab, "brands": brands})

# brand pages for the most popular brands (dataset id ~ popularity) with a real saving
cands = sorted(((b, g) for g in gens for b in g["brands"] if b["per_unit"] > g["per_unit"] * 1.05), key=lambda x: x[0]["rank"])
brand_pages, bslugs = [], set()
for b, g in cands:
    if len(brand_pages) >= N_BRAND_PAGES: break
    s = slugify(b["name"])
    if s in bslugs: continue
    bslugs.add(s); b["slug"] = s
    brand_pages.append((b, g))

all_pairs = [(b, g) for g in gens for b in g["brands"]]
savings = [pct(b["per_unit"], g["per_unit"]) for b, g in all_pairs]
median_saving = int(statistics.median(savings))
n_brands = len(all_pairs)
print(f"generics {len(gens)}, brand names {n_brands}, brand pages {len(brand_pages)}, median saving {median_saving}%")

# ------------------------------------------------------------------ JSON for the browser
os.makedirs(os.path.join(ROOT, "data", "idx"), exist_ok=True)
for f in os.listdir(os.path.join(ROOT, "data", "idx")):
    os.remove(os.path.join(ROOT, "data", "idx", f))
gidx = {g["slug"]: i for i, g in enumerate(gens)}
write("data/generics.json", json.dumps(
    [[g["slug"], g["name"], round(g["per_unit"], 4), g["mrp"], g["unit_size"], g["form"], g["label"], g["units"]] for g in gens],
    ensure_ascii=False, separators=(",", ":")))
shards = collections.defaultdict(list)
for b, g in all_pairs:
    n = re.sub(r"[^a-z0-9]", "", b["name"].lower())
    if len(n) < 2: continue
    shards[n[:2]].append((b["rank"], [b["name"], short_mfr(b["mfr"]), b["price"], b["units"], gidx[g["slug"]], b.get("slug", 0)]))
for k, rows in shards.items():
    rows.sort(key=lambda r: r[0])
    write(f"data/idx/{k}.json", json.dumps([r[1] for r in rows], ensure_ascii=False, separators=(",", ":")))

def fnum(x):
    try: return float(x)
    except (TypeError, ValueError): return None
stores = []
for k in kendras:
    la, lo = fnum(k["latitude"]), fnum(k["longitude"])
    if not (la and lo and 6 < la < 37 and 68 < lo < 98): la = lo = None
    stores.append({"lat": la, "lng": lo, "pin": k["pinCode"] or 0, "addr": re.sub(r"\s+", " ", (k["kendraAddress"] or "").strip(" ,>")),
                   "district": (k["districtName"] or "Other").strip(), "state": (k["stateName"] or "Other").strip(), "code": k["storeCode"]})
write("data/stores.json", json.dumps(
    [[round(s["lat"], 5), round(s["lng"], 5), s["pin"], s["addr"], s["district"], s["state"], s["code"]] for s in stores if s["lat"]],
    ensure_ascii=False, separators=(",", ":")))

# ------------------------------------------------------------------ components
def unit_word(form, n=2):
    return form if n == 1 else form + "s"

def compare_card(b, g, static=False, path=None):
    """Plain comparison box. app.js renders the same markup for search results."""
    unit = g["form"]
    p = pct(b["per_unit"], g["per_unit"])
    path = path or f"/brand/{b.get('slug') or ''}/"
    good = p > 0
    n = b["units"]
    gen_same = g["per_unit"] * n
    if good:
        summary = (f'<p class="saving">{n} {unit_word(unit, n)} of the generic would cost <b>{rs(gen_same)}</b> instead of {rs(b["price"])}. '
                   f'That\'s <b>{rs(b["price"] - gen_same)} less ({p}%)</b>.</p>'
                   f'<p>At <select aria-label="{unit}s per day"><option>1</option><option selected>2</option><option>3</option><option>4</option></select> '
                   f'{unit}s a day, you\'d save about <output></output>.</p>')
    else:
        summary = f'<p class="saving">This brand is already cheaper than the Jan Aushadhi version, by {rs(g["per_unit"] - b["per_unit"])} per {unit}.</p>'
    return f"""
<div class="cmp"{' data-static' if static else ''} data-brand="{E(b['name'])}" data-brand-unit="{b['per_unit']:.4f}" data-generic-unit="{g['per_unit']:.4f}" data-unit="{unit}" data-path="{path}">
<table>
<tr><td><b>{E(b['name'])}</b><br><small>{E(short_mfr(b['mfr']))} · {rs(b['price'])} for {n}</small></td><td class="price"><span class="{'struck' if good else ''}">{rs(b['per_unit'])}</span><br><small>per {unit}</small></td></tr>
<tr class="gen"><td><b>Jan Aushadhi {E(g['label'])}</b><br><small>{E(g['name'])} · {rs(g['mrp'])} for {E(g['unit_size'])}</small></td><td class="price">{rs(g['per_unit'])}<br><small>per {unit}</small></td></tr>
</table>
<div class="body">{summary}
<div class="links"><button type="button" data-share>Send this on WhatsApp</button><a href="{BASE}/stores/" data-track="find_store_cta">Find a Kendra near you</a><a href="{BASE}/medicine/{g['slug']}/" data-track="open_generic_page">All brands of {E(g['label'])}</a></div></div>
<p class="check">Before buying, check that your strip lists <b>{E(g['label'])}</b> and nothing else. If it has an extra ingredient, this isn't the same medicine.</p>
</div>"""

def brand_table(g, brands, limit=30):
    rows = []
    for b in brands[:limit]:
        p = pct(b["per_unit"], g["per_unit"])
        name = f'<a href="{BASE}/brand/{b["slug"]}/">{E(b["name"])}</a>' if b.get("slug") else E(b["name"])
        rows.append(f'<tr><td>{name}<br><small>{E(short_mfr(b["mfr"]))}</small></td><td class="n hide-sm">{rs(b["price"])}<br><small>{b["units"]} {g["form"]}s</small></td>'
                    f'<td class="n">{rs(b["per_unit"])}</td><td class="n {"save" if p > 0 else "dear"}">{p}%</td></tr>')
    return f"""<div class="scroll"><table>
<thead><tr><th>Brand</th><th class="n hide-sm">Pack</th><th class="n">Per {g['form']}</th><th class="n">Saving</th></tr></thead>
<tbody><tr class="ja"><td><b>Jan Aushadhi</b><br><small>{E(g['name'])}</small></td><td class="n hide-sm">{rs(g['mrp'])}<br><small>{E(g['unit_size'])}</small></td><td class="n"><b>{rs(g['per_unit'])}</b></td><td class="n">–</td></tr>
{''.join(rows)}</tbody></table></div>"""

def disclaimer():
    return ('<p class="note">Same salt and strength means the medicines should work the same way, but please check with your doctor '
            'or pharmacist first. Thyroid, epilepsy and heart-rhythm medicines in particular may need a check-up after you change brands.</p>')

# ------------------------------------------------------------------ pages
POPULAR = ["Dolo 650 Tablet", "PAN 40 Tablet", "Augmentin 625 Duo Tablet", "Telma 40 Tablet", "Allegra 120mg Tablet",
           "Combiflam Tablet", "Ecosprin 75 Tablet", "Thyronorm 50mcg Tablet", "Januvia 100mg Tablet", "Ultracet Tablet",
           "Rosuvas 10 Tablet", "Zerodol-P Tablet", "Montair 10 Tablet", "Azithral 500 Tablet", "Glycomet-GP 1 Tablet PR",
           "Amlong 5 Tablet", "Atarax 25mg Tablet", "Shelcal 500 Tablet"]

def build_home():
    names = {b["name"]: (b, g) for g in gens for b in g["brands"]}
    pop = [names[n] for n in POPULAR if n in names]
    examples = "".join(f'<button type="button" data-pick="{E(b["name"])}">{E(b["name"].replace(" Tablet", "").replace(" Capsule", ""))}</button>' for b, g in pop[:6])
    rows = "".join(
        f'<tr><td><a href="{BASE}/brand/{b["slug"]}/">{E(b["name"])}</a></td><td>{E(g["label"])}</td>'
        f'<td class="n">{rs(b["per_unit"])}</td><td class="n">{rs(g["per_unit"])}</td><td class="n save">{pct(b["per_unit"], g["per_unit"])}%</td></tr>'
        for b, g in pop if b.get("slug"))
    top_cities = sorted(((st, d, len(v)) for st, ds in by_state.items() for d, v in ds.items()), key=lambda x: -x[2])[:12]
    cities = ", ".join(f'<a href="{BASE}/stores/{slugify(st)}/{slugify(d)}/">{E(d)}</a> <small>({n})</small>' for st, d, n in top_cities)
    faq_ld, faq_html = faq_block([
        ("What is Jan Aushadhi?", "A Government of India scheme, run by PMBI, that sells unbranded generic medicines through Jan Aushadhi Kendras. The medicines contain the same salts as the big brands and usually cost much less."),
        ("Is the generic as good as the brand?", "In India a generic with the same salt, strength and form as a brand is meant to work the same way, and PMBI has every batch tested. Your doctor or pharmacist can tell you if switching is fine in your case."),
        ("Why is the price at the Kendra different?", "Jan Aushadhi prices here are from PMBI's own list. Brand prices come from an older public dataset, so a brand's MRP today may be different. The price printed on the strip is the one that counts."),
        ("My medicine isn't listed. Why?", "Either Jan Aushadhi doesn't make that exact salt and strength, or it's a syrup, injection or cream, which I haven't added yet. Only tablets and capsules are compared for now."),
    ])
    site_ld = {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE + "/", "inLanguage": "en-IN",
               "potentialAction": {"@type": "SearchAction", "target": SITE + "/?q={search_term_string}", "query-input": "required name=search_term_string"}}
    h = head(f"{NAME}: Jan Aushadhi Price Finder for Branded Medicines",
             f"Type a medicine like Dolo 650 or Pan 40 and see the Jan Aushadhi generic with the same salt, its price, and the nearest Jan Aushadhi Kendra. Brands cost {median_saving}% more on average.",
             "/", [site_ld, faq_ld])
    h += f"""
<main id="main" class="wrap">
  <h1>Is there a cheaper Jan Aushadhi version of your medicine?</h1>
  <p class="lead">Type the brand name from your strip. If Jan Aushadhi sells the same salt in the same strength, you'll see both prices side by side.</p>
  <form class="search" role="search" onsubmit="return false">
    <label class="skip" for="q">Medicine name</label>
    <input id="q" type="search" autocomplete="off" placeholder="e.g. Dolo 650" aria-controls="suggest" aria-autocomplete="list">
    <ul id="suggest" class="suggest" role="listbox"></ul>
  </form>
  <p class="examples">Try {examples}</p>
  <div id="result" aria-live="polite"></div>

  <h2>Some common medicines</h2>
  <p>Price per tablet or capsule. The brand prices are from the dataset I used and may have changed a little.</p>
  <div class="scroll"><table>
    <thead><tr><th>Brand</th><th>Salt</th><th class="n">Brand</th><th class="n">Jan Aushadhi</th><th class="n">Cheaper by</th></tr></thead>
    <tbody>{rows}</tbody></table></div>
  <p><a href="{BASE}/medicines/">See all {len(gens)} medicines</a></p>

  <h2>Where to buy</h2>
  <p>There are {len(kendras):,} Jan Aushadhi Kendras on PMBI's list. <a href="{BASE}/stores/">Find the ones near you</a> using your location or PIN code.
  Cities with the most Kendras: {cities}.</p>

  <h2>Why I made this</h2>
  <p>Jan Aushadhi's full price list is public, but it's sorted by salt name, while people know their medicines by brand name. So most of us never find out that the strip we buy every month has a version that costs a fraction of the price. This site joins the two lists together.</p>
  <p>Across the {n_brands:,} brands I could match, the typical brand costs {median_saving}% more than the Jan Aushadhi version with the same salt. <a href="{BASE}/about/">Here's exactly how the matching works</a>, including what it can get wrong.</p>

  <h2>Questions</h2>
  {faq_html}
  {disclaimer()}
</main>
"""
    write("index.html", h + FOOT)

def build_generic(g, related):
    path = f"/medicine/{g['slug']}/"
    bl = g["brands"]
    avg_b = statistics.mean(b["per_unit"] for b in bl)
    top_names = [b["name"].replace(" Tablet", "").replace(" Capsule", "") for b in bl[:3]]
    form = g["form"]
    title = f"{g['label']} {form.capitalize()}: Jan Aushadhi Price {rs(g['per_unit'])}/{form} vs {', '.join(top_names[:2])}"
    desc = (f"Jan Aushadhi {g['label']} {form} costs {rs(g['mrp'])} for {g['unit_size']} ({rs(g['per_unit'])} per {form}). "
            f"Compare {len(bl)} brands like {', '.join(top_names)}.")
    cld, ch = crumbs([("Home", "/"), ("Medicines", "/medicines/"), (g["label"], path)])
    drug_ld = {"@context": "https://schema.org", "@type": "Drug", "name": g["label"], "nonProprietaryName": g["label"],
               "dosageForm": form.capitalize(), "activeIngredient": [f"{salt_title(s)} {strength_label(st)}" for s, st in g["comps"]],
               "offers": {"@type": "Offer", "price": round(g["mrp"], 2), "priceCurrency": "INR", "seller": {"@type": "Organization", "name": "Jan Aushadhi (PMBI)"}}}
    faq_ld, faq_html = faq_block([
        (f"What does Jan Aushadhi {g['label']} cost?", f"{rs(g['mrp'])} for {g['unit_size']}, which is {rs(g['per_unit'])} per {form} (PMBI list)."),
        (f"Which brands contain {g['label']}?", f"{len(bl)} brands in my data, for example {', '.join(b['name'] for b in bl[:5])}."),
    ])
    best = bl[0]
    rel = ", ".join(f'<a href="{BASE}/medicine/{r["slug"]}/">{E(r["label"])}</a>' for r in related)
    h = head(title, desc, path, [cld, drug_ld, faq_ld])
    h += f"""
<main id="main" class="wrap">
  {ch}
  <h1>{E(g['label'])} {form}</h1>
  <p class="lead">Jan Aushadhi sells this as “{E(g['name'])}” for <b>{rs(g['mrp'])}</b> ({E(g['unit_size'])}), or {rs(g['per_unit'])} per {form}.
  I found {len(bl)} brands with the same salt and strength. On average they cost {rs(avg_b)} per {form}.</p>
  <p class="muted">{E(g['group'])}{' · sustained release' if g['release'] == 'mr' else ''}</p>
  {compare_card(best, g, path=path)}
  <h2>All brands</h2>
  <p>Most common first. Price per {form} makes different pack sizes comparable.</p>
  {brand_table(g, bl)}
  {f'<p class="muted">Showing 30 of {len(bl)} brands.</p>' if len(bl) > 30 else ''}
  {faq_html}
  {disclaimer()}
  {f'<h2>Other {E(g["group"].split("(")[0].strip().lower())} medicines</h2><p class="inline-list">{rel}</p>' if rel else ''}
</main>
"""
    write(f"medicine/{g['slug']}/index.html", h + FOOT)

def build_brand(b, g):
    path = f"/brand/{b['slug']}/"
    p = pct(b["per_unit"], g["per_unit"])
    form = g["form"]
    short = b["name"].replace(" Tablet", "").replace(" Capsule", "")
    title = f"{short} Generic Alternative: Jan Aushadhi {g['label']} at {rs(g['per_unit'])}/{form}"
    desc = (f"{b['name']} costs {rs(b['per_unit'])} per {form}. The Jan Aushadhi medicine with the same salt ({g['label']}) costs "
            f"{rs(g['per_unit'])}, {p}% less. Prices, other brands and nearby Jan Aushadhi Kendras.")
    cld, ch = crumbs([("Home", "/"), (g["label"], f"/medicine/{g['slug']}/"), (short, path)])
    faq_ld, faq_html = faq_block([
        (f"What is the generic name of {short}?", f"{short} contains {g['label']}. Jan Aushadhi sells the same thing as “{g['name']}”."),
        (f"Can I take the Jan Aushadhi version instead of {short}?", "It has the same salt in the same strength, so it should work the same way. Ask your doctor or pharmacist before switching."),
    ])
    others = [x for x in g["brands"] if x["name"] != b["name"]][:12]
    h = head(title, desc, path, [cld, faq_ld])
    h += f"""
<main id="main" class="wrap">
  {ch}
  <h1>{E(short)}: generic alternative and price</h1>
  <p class="lead">{E(b['name'])} by {E(short_mfr(b['mfr']))} contains {E(g['label'])}. Jan Aushadhi sells the same salt for {rs(g['per_unit'])} per {form}, compared with {rs(b['per_unit'])} for {E(short)}.</p>
  {compare_card(b, g, static=True, path=path)}
  <h2>Other brands with {E(g['label'])}</h2>
  {brand_table(g, others, 12)}
  <p><a href="{BASE}/medicine/{g['slug']}/">All {len(g['brands'])} brands of {E(g['label'])}</a></p>
  {faq_html}
  {disclaimer()}
</main>
"""
    write(f"brand/{b['slug']}/index.html", h + FOOT)

def build_medicines_index():
    groups = collections.defaultdict(list)
    for g in gens: groups[g["group"]].append(g)
    cld, ch = crumbs([("Home", "/"), ("Medicines", "/medicines/")])
    order = sorted(groups, key=lambda k: -len(groups[k]))
    toc = " · ".join(f'<a href="#{slugify(k)}">{E(k)}</a>' for k in order)
    body = ""
    for grp in order:
        items = sorted(groups[grp], key=lambda g: g["label"])
        body += f'<h2 id="{slugify(grp)}">{E(grp)} <small>({len(items)})</small></h2><p class="inline-list">' + \
                ", ".join(f'<a href="{BASE}/medicine/{g["slug"]}/">{E(g["label"])} {g["form"]}</a>' for g in items) + "</p>"
    h = head(f"All {len(gens)} Jan Aushadhi Tablets and Capsules with Brand Prices | {NAME}",
             f"{len(gens)} Jan Aushadhi tablets and capsules, grouped by type, each compared with the branded medicines that have the same salt.",
             "/medicines/", [cld])
    h += f"""<main id="main" class="wrap">{ch}<h1>All medicines</h1>
<p class="lead">These are the {len(gens)} Jan Aushadhi tablets and capsules I could match with at least one brand, grouped the way PMBI groups them.</p>
<p class="muted">{toc}</p>{body}</main>"""
    write("medicines/index.html", h + FOOT)

# stores ---------------------------------------------------------------
by_state = collections.defaultdict(lambda: collections.defaultdict(list))
for s in stores: by_state[s["state"]][s["district"]].append(s)

def store_li(s):
    dirl = f'https://www.google.com/maps/dir/?api=1&destination={s["lat"]},{s["lng"]}' if s["lat"] else f'https://www.google.com/maps/search/?api=1&query={html.escape(s["addr"] + " " + str(s["pin"]))}'
    return (f'<li class="store"><b>{E(s["addr"]) or "Address not listed"}</b><div class="meta">{E(s["district"])}, {E(s["state"])} {s["pin"]} · Kendra code {E(s["code"])}</div>'
            f'<a href="{dirl}" target="_blank" rel="noopener" data-track="store_directions">Directions</a></li>')

def build_stores():
    leaflet = ('\n  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">'
               '\n  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" defer></script>'
               f'\n  <script src="{BASE}/assets/stores.js" defer></script>')
    cld, ch = crumbs([("Home", "/"), ("Kendras", "/stores/")])
    states = sorted(by_state)
    st_html = ", ".join(f'<a href="{BASE}/stores/{slugify(st)}/">{E(st)}</a> <small>({sum(len(v) for v in by_state[st].values())})</small>' for st in states)
    h = head(f"Jan Aushadhi Kendra Near Me: {len(kendras):,} Stores on a Map | {NAME}",
             f"Find the nearest Jan Aushadhi Kendra by location or PIN code. All {len(kendras):,} Kendras from PMBI's list, with addresses and directions.",
             "/stores/", [cld], leaflet)
    h += f"""<main id="main" class="wrap">{ch}
<h1>Find a Jan Aushadhi Kendra</h1>
<p class="lead">All {len(kendras):,} Kendras from PMBI's list. Use your location or enter a PIN code. Your location stays in your browser.</p>
<div class="store-tools">
  <button id="use-loc" class="btn primary" type="button">Use my location</button>
  <form id="pin-form" style="display:flex;gap:8px"><label class="skip" for="pin">PIN code</label><input id="pin" inputmode="numeric" maxlength="6" placeholder="PIN code"><button class="btn" type="submit">Search</button></form>
</div>
<p id="store-msg" class="status-msg" aria-live="polite"></p>
<div id="map" role="region" aria-label="Map of Jan Aushadhi Kendras"></div>
<ul id="store-list" class="store-list"></ul>
<h2>By state</h2>
<p class="inline-list">{st_html}</p>
<p class="muted">Not every Kendra stocks every medicine. If you're going for something specific, it's worth calling first.</p>
</main>"""
    write("stores/index.html", h + FOOT)
    for st in states:
        ds = by_state[st]
        total = sum(len(v) for v in ds.values())
        cld, ch = crumbs([("Home", "/"), ("Kendras", "/stores/"), (st, f"/stores/{slugify(st)}/")])
        dl = ", ".join(f'<a href="{BASE}/stores/{slugify(st)}/{slugify(d)}/">{E(d)}</a> <small>({len(v)})</small>' for d, v in sorted(ds.items()))
        h = head(f"Jan Aushadhi Kendras in {st}: {total:,} Stores by District | {NAME}",
                 f"{total:,} Jan Aushadhi Kendras in {st} across {len(ds)} districts, with addresses and directions.",
                 f"/stores/{slugify(st)}/", [cld])
        h += f"""<main id="main" class="wrap">{ch}<h1>Jan Aushadhi Kendras in {E(st)}</h1>
<p class="lead">{total:,} Kendras in {len(ds)} districts.</p><p class="inline-list">{dl}</p></main>"""
        write(f"stores/{slugify(st)}/index.html", h + FOOT)
        for d, v in ds.items():
            path = f"/stores/{slugify(st)}/{slugify(d)}/"
            cld, ch = crumbs([("Home", "/"), ("Kendras", "/stores/"), (st, f"/stores/{slugify(st)}/"), (d, path)])
            v = sorted(v, key=lambda s: (s["pin"], s["code"]))
            pins = sorted({s["pin"] for s in v if s["pin"]})
            list_ld = {"@context": "https://schema.org", "@type": "ItemList", "name": f"Jan Aushadhi Kendras in {d}", "numberOfItems": len(v),
                       "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": {"@type": "Pharmacy", "name": f"Jan Aushadhi Kendra {s['code']}",
                           "address": {"@type": "PostalAddress", "streetAddress": s["addr"], "addressLocality": d, "addressRegion": st, "postalCode": str(s["pin"]), "addressCountry": "IN"},
                           **({"geo": {"@type": "GeoCoordinates", "latitude": s["lat"], "longitude": s["lng"]}} if s["lat"] else {})}} for i, s in enumerate(v[:100])]}
            h = head(f"Jan Aushadhi Kendra in {d}: {len(v)} Stores with Address & Directions",
                     f"{len(v)} Jan Aushadhi Kendras in {d}, {st}" + (f" (PIN {pins[0]} to {pins[-1]})" if len(pins) > 1 else "") + ". Addresses, PIN codes and directions.",
                     path, [cld, list_ld])
            h += f"""<main id="main" class="wrap">{ch}<h1>Jan Aushadhi Kendras in {E(d)}</h1>
<p class="lead">{len(v)} Kendra{'s' if len(v) != 1 else ''} in {E(d)}, {E(st)}, sorted by PIN code. Addresses are as listed by PMBI.
To sort by distance from you, use the <a href="{BASE}/stores/">map</a>.</p>
<ul class="store-list">{''.join(store_li(s) for s in v)}</ul></main>"""
            write(f"stores/{slugify(st)}/{slugify(d)}/index.html", h + FOOT)

def build_about():
    cld, ch = crumbs([("Home", "/"), ("About", "/about/")])
    unmatched = len(products) - len(gens)
    h = head(f"How {NAME} Works: Data Sources and Matching",
             "Where Generic Bachat's prices come from, how brands are matched to Jan Aushadhi generics, and what it can get wrong.",
             "/about/", [cld])
    h += f"""<main id="main" class="wrap">{ch}
<h1>How this works</h1>
<p class="lead">Generic Bachat is a small side project by <a href="{PORTFOLIO}?utm_source=generic_bachat&utm_medium=referral&utm_campaign=about">Chinmaya Nayak</a>, an M.Tech student at IIIT Allahabad. It doesn't sell anything and isn't connected to PMBI or the government.</p>

<h2>Where the data comes from</h2>
<p><b>Jan Aushadhi prices:</b> PMBI's product list on janaushadhi.gov.in, downloaded on {DATA_DATE}. {len(products):,} products.</p>
<p><b>Kendras:</b> PMBI's store list from the same site. {len(kendras):,} Kendras, with addresses, PIN codes and map locations.</p>
<p><b>Brand prices:</b> the open <a href="https://github.com/junioralive/Indian-Medicine-Dataset" rel="noopener">Indian Medicine Dataset</a> (MIT licence), collected from online pharmacy listings. It's a few years old, so brand prices are a guide, not a quote.</p>

<h2>How a brand is matched</h2>
<p>For each Jan Aushadhi tablet or capsule, I split the name into salts and strengths, for example “Pantoprazole 40 mg”. The same is done for every brand. Names are cleaned up so that “Amoxycillin” matches “Amoxicillin” and “Metformin Hydrochloride” matches “Metformin”, and strengths are converted to the same unit.</p>
<p>A brand only counts as a match if every salt and every strength is the same, and the form is the same (tablet or capsule). Sustained-release versions are only matched with sustained-release versions. Prices are compared per tablet, so different pack sizes are fair.</p>
<p>That gives {len(gens)} Jan Aushadhi medicines matched to {n_brands:,} brands.</p>

<h2>What it can get wrong</h2>
<p>The brand dataset only records two ingredients per medicine. So a brand with three ingredients could look like a two-ingredient one. Zerodol-SP is the example that caught me: it has serratiopeptidase on top of the two painkillers. To guard against this, two-ingredient brands are dropped when their name has a marker that usually means a third ingredient (SP, Trio, Gold, AMH and a few others), or when the same company sells a shorter-named brand with the same listed ingredients. That catches most cases, but not necessarily all, which is why every result tells you exactly what your strip should say.</p>
<p>Syrups, injections, creams and devices aren't compared yet ({unmatched:,} Jan Aushadhi products), because their pack sizes are hard to compare fairly.</p>
<p>Found a wrong match? Email me at <a href="mailto:chinmayanayak018@gmail.com?subject=Generic%20Bachat%20correction">chinmayanayak018@gmail.com</a> and I'll fix it.</p>
{disclaimer()}
</main>"""
    write("about/index.html", h + FOOT)

def build_404():
    h = head(f"Page not found | {NAME}", "This page doesn't exist.", "/404.html", robots="noindex")
    h += f"""<main id="main" class="wrap"><h1>Page not found</h1><script>var p=location.pathname;if(/^\/generic-bachat(\/|$)/.test(p))location.replace((p.slice(15)||'/')+location.search+location.hash);</script><p><a href="{BASE}/">Search for a medicine</a> or <a href="{BASE}/stores/">find a Kendra</a>.</p></main>"""
    write("404.html", h + FOOT)

def build_sitemap():
    urls = ["/", "/stores/", "/medicines/", "/about/"]
    urls += [f"/medicine/{g['slug']}/" for g in gens]
    urls += [f"/brand/{b['slug']}/" for b, g in brand_pages]
    for st, ds in by_state.items():
        urls.append(f"/stores/{slugify(st)}/")
        urls += [f"/stores/{slugify(st)}/{slugify(d)}/" for d in ds]
    body = "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}</urlset>\n')
    print("sitemap urls:", len(urls))

if __name__ == "__main__":
    for d in ("medicine", "brand", "stores", "medicines", "about"):
        shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)
    build_home()
    groups = collections.defaultdict(list)
    for g in gens: groups[g["group"]].append(g)
    for g in gens:
        rel = [x for x in groups[g["group"]] if x is not g][:10]
        build_generic(g, rel)
    for b, g in brand_pages:
        build_brand(b, g)
    build_medicines_index()
    build_stores()
    build_about()
    build_404()
    build_sitemap()
    open(os.path.join(ROOT, ".nojekyll"), "w").close()
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\nSitemap: {PORTFOLIO}sitemap.xml\n")
