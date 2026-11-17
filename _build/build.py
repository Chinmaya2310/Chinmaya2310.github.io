"""Generic Bachat static site generator.

python3 _build/match.py   # raw data -> _data/matched.json
python3 _build/build.py   # matched.json + store list -> HTML pages, JSON search index, sitemap
"""
import json, os, re, html, statistics, datetime, shutil, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "_data", "raw")
BASE = "/generic-bachat"
SITE = "https://chinmaya2310.github.io" + BASE
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

# ------------------------------------------------------------------ icons
I = {
 "logo": '<svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="18" fill="none" stroke="#d42a3c" stroke-width="3"/><circle cx="20" cy="20" r="13.5" fill="none" stroke="#d42a3c" stroke-width="1.2" stroke-dasharray="2 2"/><g transform="rotate(-35 20 20)"><rect x="10.5" y="15.5" width="19" height="9" rx="4.5" fill="#f08a24" stroke="#18203a" stroke-width="1.8"/><path d="M20 15.5h5a4.5 4.5 0 0 1 0 9h-5z" fill="#fffcf4" stroke="#18203a" stroke-width="1.8"/></g></svg>',
 "search": '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
 "sun": '<svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
 "moon": '<svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>',
 "pin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/></svg>',
 "wa": '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm5.3 14.2c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.3-.7-2.8-1.1-4.6-4-4.7-4.2-.1-.2-1.1-1.5-1.1-2.9s.7-2 1-2.3c.2-.3.5-.3.7-.3h.5c.2 0 .4 0 .6.5l.8 2c.1.2.1.4 0 .5l-.3.5-.4.4c-.1.1-.3.3-.1.6.2.3.8 1.3 1.7 2.1 1.2 1 2.1 1.3 2.4 1.5.3.1.5.1.6-.1l.9-1.1c.2-.3.4-.2.6-.1l1.9.9c.3.1.5.2.5.3.1.2.1.7-.1 1.2z"/></svg>',
 "loc": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/><circle cx="12" cy="12" r="7"/></svg>',
}

# ------------------------------------------------------------------ layout
def head(title, desc, path, jsonld=(), extra_head="", robots="index, follow"):
    url = SITE + path
    ld = "".join(f'\n  <script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in jsonld)
    return f"""<!DOCTYPE html>
<html lang="en-IN" data-base="{BASE}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{E(title)}</title>
  <meta name="description" content="{E(desc)}">
  <meta name="robots" content="{robots}">
  <link rel="canonical" href="{url}">
  <link rel="icon" href="{BASE}/assets/favicon.svg" type="image/svg+xml">
  <meta name="theme-color" content="#0b6e4f">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{NAME}">
  <meta property="og:locale" content="en_IN">
  <meta property="og:title" content="{E(title)}">
  <meta property="og:description" content="{E(desc)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SITE}/assets/og.png">
  <meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">{ld}
  <script>try{{var t=localStorage.getItem('theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
  <link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800&family=Caveat:wght@600;700&family=JetBrains+Mono:wght@500;700&display=swap">
  <link rel="stylesheet" href="{BASE}/assets/style.css">{extra_head}
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA}',{{content_group:'{content_group(path)}'}});</script>
  <script src="{BASE}/assets/app.js" defer></script>
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <header class="site-header"><nav aria-label="Main">
    <a class="logo" href="{BASE}/">{I['logo']}<span>{NAME}<small>दवा वही · दाम कम</small></span></a>
    <ul class="nav-links">
      <li><a href="{BASE}/#search">Compare prices</a></li>
      <li><a href="{BASE}/stores/">Find a Kendra</a></li>
      <li><a href="{BASE}/medicines/">All medicines</a></li>
      <li><a href="{BASE}/about/">How it works</a></li>
    </ul>
    <button class="theme-toggle" type="button" aria-label="Switch light or dark theme">{I['sun']}{I['moon']}</button>
  </nav></header>
"""

def content_group(path):
    for k in ("medicine", "brand", "stores", "about", "medicines"):
        if path.startswith(f"/{k}/"): return k
    return "home"

FOOT = f"""
  <footer class="site-footer"><div class="wrap">
    <p><b>Medical disclaimer:</b> {NAME} compares prices only. It is not medical advice. Generic and branded medicines with the same salt and strength are meant to be interchangeable, but always confirm with your doctor or pharmacist before switching, and check the composition printed on the pack.</p>
    <p>Not affiliated with PMBI, the Department of Pharmaceuticals or the Government of India. Jan Aushadhi prices and store list from the official PMBI website ({DATA_DATE}); brand prices from a public dataset and may be out of date.
    · <a href="{BASE}/about/">Methodology &amp; sources</a> · <a href="{BASE}/medicines/">All medicines</a> · <a href="{BASE}/stores/">Store directory</a></p>
    <p>Built by <a href="https://chinmaya2310.github.io/?utm_source=generic_bachat&utm_medium=referral&utm_campaign=footer" data-track="footer_author">Chinmaya Kumar Nayak</a> as an independent public-interest project.</p>
  </div></footer>
</body>
</html>
"""

def crumbs(items):
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + p} for i, (n, p) in enumerate(items)]}
    h = " / ".join(f'<a href="{BASE}{p}">{E(n)}</a>' if i < len(items) - 1 else f'<span aria-current="page">{E(n)}</span>'
                   for i, (n, p) in enumerate(items))
    return ld, f'<nav class="crumbs" aria-label="Breadcrumb">{h}</nav>'

def faq_block(qas):
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", a)}} for q, a in qas]}
    h = "".join(f"<details><summary>{E(q)}</summary><p>{a}</p></details>" for q, a in qas)
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
def compare_card(b, g, static=False, path=None, wide=False):
    unit = g["form"]
    p = pct(b["per_unit"], g["per_unit"])
    path = path or f"/brand/{b.get('slug') or ''}/"
    good = p > 0
    n = b["units"]
    gen_pack = g["per_unit"] * n
    save = b["price"] - gen_pack
    stamp = f'<div class="stamp">{p}%<small>बचत</small></div>' if good else ''
    total = (f'<div class="r-total"><span>YOU SAVE</span>{stamp}<span class="amt">{rs(save)}</span></div>' if good else
             f'<div class="r-total neg"><span>NO SAVING</span><span class="amt">brand is cheaper</span></div>')
    return f"""
<article class="compare receipt{' wide' if wide else ''}"{' data-static' if static else ''} data-brand="{E(b['name'])}" data-brand-unit="{b['per_unit']:.4f}" data-generic-unit="{g['per_unit']:.4f}" data-unit="{unit}" data-path="{path}">
  <header class="r-head"><b>GENERIC BACHAT</b><span>Price check · {n} {unit}s</span></header>
  <div class="r-line brand"><div><b>{E(b['name'])}</b><small>{E(short_mfr(b['mfr']))} · {rs(b['per_unit'])}/{unit}</small></div><span class="amt{' struck' if good else ''}">{rs(b['price'])}</span></div>
  <div class="r-line gen"><div><b>Jan Aushadhi {E(g['label'])}</b><small>Same salt · {rs(g['per_unit'])}/{unit}</small></div><span class="amt">{rs(gen_pack)}</span></div>
  {total}
  {f'<div class="r-calc"><label for="calc-n">Taking</label><select id="calc-n"><option value="1">1</option><option value="2" selected>2</option><option value="3">3</option><option value="4">4</option></select> {unit}s a day saves <output></output></div>' if good else ''}
  <div class="r-actions"><button class="btn btn-wa" type="button" data-share>{I['wa']}Share on WhatsApp</button>
    <a class="btn btn-ghost" href="{BASE}/stores/" data-track="find_store_cta">{I['pin']}Nearest Kendra</a>
    <button class="btn btn-ghost" type="button" data-copy>Copy link</button></div>
  <p class="r-note"><b>Check your strip:</b> the composition should read exactly <b>{E(g['label'])}</b>, nothing else. Jan Aushadhi pack: {E(g['name'])}, {E(g['unit_size'])} for {rs(g['mrp'])}. Brand price from a public dataset; may have changed. Ask your doctor or pharmacist before switching.</p>
</article>"""

def brand_table(g, brands, limit=30):
    rows = []
    for b in brands[:limit]:
        p = pct(b["per_unit"], g["per_unit"])
        name = f'<a href="{BASE}/brand/{b["slug"]}/">{E(b["name"])}</a>' if b.get("slug") else E(b["name"])
        rows.append(f'<tr><td>{name}<br><small class="muted">{E(short_mfr(b["mfr"]))}</small></td><td class="num">{rs(b["price"])}<br><small class="muted">{b["units"]} {g["form"]}s</small></td>'
                    f'<td class="num">{rs(b["per_unit"])}</td><td class="num {"pos" if p > 0 else "negv"}">{p}%</td></tr>')
    return f"""<div class="table-wrap"><table>
<thead><tr><th>Brand</th><th class="num">Pack price</th><th class="num">Per {g['form']}</th><th class="num">Generic saves</th></tr></thead>
<tbody><tr class="ja"><td><b>Jan Aushadhi: {E(g['name'])}</b><br><small class="muted">PMBI drug code {g['drug_code']}</small></td><td class="num">{rs(g['mrp'])}<br><small class="muted">{E(g['unit_size'])}</small></td><td class="num"><b>{rs(g['per_unit'])}</b></td><td class="num">—</td></tr>
{''.join(rows)}</tbody></table></div>"""

def disclaimer():
    return f'<div class="disclaimer"><b>Before you switch:</b> show this page to your doctor or pharmacist. Medicines with the same salt and strength are meant to work the same way, but some (for example thyroid, epilepsy or heart-rhythm medicines) need monitoring when you change makers. Never stop or change a dose on your own.</div>'

# ------------------------------------------------------------------ pages
POPULAR = ["Dolo 650 Tablet", "PAN 40 Tablet", "Augmentin 625 Duo Tablet", "Telma 40 Tablet", "Allegra 120mg Tablet",
           "Combiflam Tablet", "Ecosprin 75 Tablet", "Thyronorm 50mcg Tablet", "Januvia 100mg Tablet", "Ultracet Tablet",
           "Rosuvas 10 Tablet", "Zerodol-P Tablet"]

def build_home():
    names = {b["name"]: (b, g) for g in gens for b in g["brands"]}
    pop = [n for n in POPULAR if n in names]
    top = [(b, g) for b, g in brand_pages[:80] if pct(b["per_unit"], g["per_unit"]) >= 60][:10]
    faq_ld, faq_html = faq_block([
        ("What is a Jan Aushadhi medicine?", "Jan Aushadhi medicines are unbranded generic medicines sold through Pradhan Mantri Bhartiya Janaushadhi Kendras, a Government of India scheme run by PMBI. They contain the same active ingredients (salts) as branded medicines, usually at a much lower price."),
        ("Are generic medicines as good as branded ones?", "In India, a generic and a branded medicine with the same salt, strength and dosage form are meant to be therapeutically equivalent, and Jan Aushadhi products are tested by NABL-accredited labs. Your doctor or pharmacist can confirm whether switching is right for you."),
        ("How does Generic Bachat find the generic?", "We match the salt (active ingredient), its strength and the dosage form, such as 650 mg paracetamol tablet, between the brand and the official Jan Aushadhi product list, and then compare the price per tablet or capsule."),
        ("Why might the price at the shop be different?", "Jan Aushadhi prices come from the official PMBI product list. Brand prices come from a public dataset of online pharmacy listings, so a brand's current MRP may be higher or lower. Always check the MRP printed on the strip."),
        ("Where can I buy Jan Aushadhi medicines?", f'At any of the 21,000+ Jan Aushadhi Kendras across India. Use our <a href="{BASE}/stores/">store finder</a> to see the nearest ones on a map.'),
    ])
    site_ld = {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE + "/", "inLanguage": "en-IN",
               "potentialAction": {"@type": "SearchAction", "target": SITE + "/?q={search_term_string}", "query-input": "required name=search_term_string"}}
    org_ld = {"@context": "https://schema.org", "@type": "Organization", "name": NAME, "url": SITE + "/", "logo": SITE + "/assets/favicon.svg",
              "founder": {"@type": "Person", "name": "Chinmaya Kumar Nayak", "url": "https://chinmaya2310.github.io/"}}
    h = head(f"{NAME}: Find the Cheaper Jan Aushadhi Generic for Your Medicine",
             f"Type your branded medicine (Dolo 650, Pan 40, Telma 40…) and see the Jan Aushadhi generic with the same salt, how much you save (typically {median_saving}%), and the nearest Jan Aushadhi Kendra.",
             "/", [site_ld, org_ld, faq_ld])
    chips = "".join(f'<button class="chip" type="button" data-pick="{E(n)}">{E(n.replace(" Tablet", "").replace(" Capsule", ""))}</button>' for n in pop)
    top_html = "".join(f'<a class="price-tag" href="{BASE}/brand/{b["slug"]}/" data-track="top_saving_click"><span><b>{E(b["name"])}</b><small>{E(g["label"])} · {rs(b["per_unit"])} → {rs(g["per_unit"])}</small></span><span class="pct">−{pct(b["per_unit"], g["per_unit"])}%</span></a>' for b, g in top)
    demo = names.get("Dolo 650 Tablet")
    demo_html = compare_card(demo[0], demo[1], path="/brand/dolo-650-tablet/") if demo else ""
    h += f"""
  <main id="main">
    <section class="hero" id="search"><div class="wrap hero-grid">
      <div>
        <span class="kicker-hi">दवा वही, दाम कम</span>
        <h1>Same salt.<br>Same strength.<br><span class="hl">Up to 90% less.</span></h1>
        <p class="lead">Type the medicine on your prescription. See the Jan Aushadhi generic with the identical salt, what it costs, and the nearest Kendra that sells it.</p>
        <div class="search-note"><span class="hand">type the name on your strip</span><svg viewBox="0 0 46 34" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M2 6c14-4 30 0 36 18"/><path d="M31 19l7 6 4-9"/></svg></div>
        <form class="search" role="search" onsubmit="return false">
          {I['search']}
          <label class="skip" for="q">Search a branded medicine</label>
          <input id="q" type="search" autocomplete="off" placeholder="Dolo 650, Pan 40, Telma 40…" aria-controls="suggest" aria-autocomplete="list">
          <ul id="suggest" class="suggest" role="listbox"></ul>
        </form>
        <div class="popular"><span>Try:</span>{chips}</div>
      </div>
      <div class="hero-demo"><span class="tape-strip"></span>{demo_html.replace('id="calc-n"', 'id="calc-demo"').replace('for="calc-n"', 'for="calc-demo"')}<span class="hand">← real prices</span></div>
    </div>
    <div class="wrap"><div id="result" style="margin-top:30px" aria-live="polite"></div>
      <div class="tape">
        <div><b>{median_saving}%</b><span>typical saving</span></div>
        <div><b>{n_brands // 1000}k+</b><span>brands compared</span></div>
        <div><b>{len(products):,}</b><span>Jan Aushadhi products</span></div>
        <div><b>{len(kendras):,}</b><span>Kendras mapped</span></div>
      </div></div>
    </section>

    <section class="section alt"><div class="wrap">
      <div class="section-head reveal"><span class="eyebrow">How it works</span><h2>Three steps to a <span class="hl">smaller bill</span></h2></div>
      <div class="steps">
        <div class="step reveal"><span class="n">1.</span><h3>Search your brand</h3><p>Type the name printed on your strip. We know {n_brands // 1000}k+ branded tablets and capsules.</p></div>
        <div class="step reveal"><span class="n">2.</span><h3>Same salt, cheaper</h3><p>We match the active ingredient, strength and form against the official Jan Aushadhi list, and compare the price per tablet.</p></div>
        <div class="step reveal"><span class="n">3.</span><h3>Buy it nearby</h3><p>Find the closest of {len(kendras):,} Jan Aushadhi Kendras, with directions. Share the saving with family on WhatsApp.</p></div>
      </div>
    </div></section>

    <section class="section"><div class="wrap">
      <div class="section-head reveal"><span class="eyebrow">Biggest price gaps</span><h2>Popular brands, <span class="hl">marked down</span></h2><p>Price per tablet or capsule: the brand vs. the Jan Aushadhi generic with the same salt.</p></div>
      <div class="tags-grid">{top_html}</div>
      <p style="margin-top:22px"><a class="btn btn-ghost" href="{BASE}/medicines/">Browse all {len(gens)} medicines →</a></p>
    </div></section>

    <section class="section alt"><div class="wrap store-cta">
      <div class="reveal"><span class="eyebrow">Store finder</span><h2>{len(kendras):,} Kendras. <span class="hl">One is near you.</span></h2>
        <p class="muted">Use your location or PIN code to see the nearest Jan Aushadhi Kendras on a map, with one-tap directions.</p>
        <a class="btn btn-leaf" href="{BASE}/stores/" data-track="find_store_cta">{I['pin']}Find the nearest Kendra</a></div>
      <div class="board reveal"><h3>Most Kendras</h3><div class="links-cloud">{popular_cities_html()}</div></div>
    </div></section>

    <section class="section"><div class="wrap"><div class="prose">
      <div class="section-head"><span class="eyebrow">Questions</span><h2>Frequently asked</h2></div>
      {faq_html}
      {disclaimer()}
    </div></div></section>
  </main>
"""
    write("index.html", h + FOOT)

def build_generic(g, related):
    path = f"/medicine/{g['slug']}/"
    bl = g["brands"]
    pricier = [b for b in bl if b["per_unit"] > g["per_unit"]]
    avg_b = statistics.mean(b["per_unit"] for b in bl)
    top_names = [b["name"].replace(" Tablet", "").replace(" Capsule", "") for b in bl[:3]]
    form = g["form"]
    title = f"{g['label']} {form.capitalize()}: Jan Aushadhi Price {rs(g['per_unit'])}/{form} vs {', '.join(top_names[:2])}"
    desc = (f"Jan Aushadhi {g['label']} {form} costs {rs(g['mrp'])} for {g['unit_size']} ({rs(g['per_unit'])} per {form}). "
            f"Compare {len(bl)} brands like {', '.join(top_names)} and save up to {max(pct(b['per_unit'], g['per_unit']) for b in bl)}%.")
    cld, ch = crumbs([("Home", "/"), ("Medicines", "/medicines/"), (g["label"], path)])
    drug_ld = {"@context": "https://schema.org", "@type": "Drug", "name": g["label"], "nonProprietaryName": g["label"],
               "dosageForm": form.capitalize(), "activeIngredient": [f"{salt_title(s)} {strength_label(st)}" for s, st in g["comps"]],
               "offers": {"@type": "Offer", "price": round(g["mrp"], 2), "priceCurrency": "INR", "seller": {"@type": "Organization", "name": "Jan Aushadhi (PMBI)"}}}
    faq_ld, faq_html = faq_block([
        (f"What is the Jan Aushadhi price of {g['label']} {form}?", f"{rs(g['mrp'])} for {g['unit_size']} ({rs(g['per_unit'])} per {form}), as listed by PMBI ({DATA_DATE})."),
        (f"Which brands contain {g['label']}?", f"{len(bl)} brands in our data, including {', '.join(b['name'] for b in bl[:5])}."),
        (f"How much can I save with the generic?", f"The average brand in our data costs {rs(avg_b)} per {form}; {len(pricier)} of {len(bl)} brands cost more than the Jan Aushadhi generic."),
    ])
    best = max(bl[:20], key=lambda b: b["per_unit"])
    rel = "".join(f'<a class="chip" href="{BASE}/medicine/{r["slug"]}/">{E(r["label"])}</a>' for r in related)
    h = head(title, desc, path, [cld, drug_ld, faq_ld])
    h += f"""
  <main id="main" class="wrap">
    {ch}
    <div class="page-split"><header class="page-head">
      <ul class="pills"><li>{E(g['group'])}</li><li>{form.capitalize()}</li>{'<li>Sustained release</li>' if g['release'] == 'mr' else ''}</ul>
      <h1>{E(g['label'])} {form}: <span class="hl">Jan Aushadhi price</span> vs brands</h1>
      <p class="lead">The Jan Aushadhi generic costs <b>{rs(g['per_unit'])} per {form}</b> ({rs(g['mrp'])} for {E(g['unit_size'])}). We found <b>{len(bl)} brands</b> with the same salt and strength; the average costs {rs(avg_b)} per {form}.</p>
    </header>
    {compare_card(best, g, path=path)}</div>
    <div class="prose">
      <h2>All brands of {E(g['label'])} vs. Jan Aushadhi</h2>
      <p class="muted">Most-used brands first. Price per {form} lets you compare different pack sizes.</p>
    </div>
    {brand_table(g, bl)}
    {f'<p class="muted" style="font-size:.9rem;margin-top:10px">Showing 30 of {len(bl)} brands.</p>' if len(bl) > 30 else ''}
    <div class="prose">
      <h2>Questions</h2>{faq_html}
      {disclaimer()}
      {f'<h2>Related medicines</h2><div class="links-cloud">{rel}</div>' if rel else ''}
    </div>
  </main>
"""
    write(f"medicine/{g['slug']}/index.html", h + FOOT)

def build_brand(b, g):
    path = f"/brand/{b['slug']}/"
    p = pct(b["per_unit"], g["per_unit"])
    form = g["form"]
    short = b["name"].replace(" Tablet", "").replace(" Capsule", "")
    title = f"{short} Generic Alternative: Jan Aushadhi {g['label']} at {rs(g['per_unit'])}/{form} (Save {p}%)"
    desc = (f"{b['name']} costs {rs(b['per_unit'])} per {form}. The Jan Aushadhi generic with the same salt ({g['label']}) costs "
            f"{rs(g['per_unit'])}, {p}% less. See the monthly saving and the nearest Jan Aushadhi Kendra.")
    cld, ch = crumbs([("Home", "/"), (g["label"], f"/medicine/{g['slug']}/"), (short, path)])
    faq_ld, faq_html = faq_block([
        (f"What is the generic name of {short}?", f"{short} contains {g['label']}. The Jan Aushadhi product with the same composition is “{g['name']}”."),
        (f"What is the cheaper substitute for {short}?", f"The Jan Aushadhi generic {g['label']} {form} costs {rs(g['per_unit'])} per {form} vs. {rs(b['per_unit'])} for {short}, a saving of about {p}%."),
        (f"Can I replace {short} with the Jan Aushadhi generic?", "Medicines with the same salt, strength and dosage form are meant to be interchangeable, but ask your doctor or pharmacist before switching."),
    ])
    others = [x for x in g["brands"] if x["name"] != b["name"]][:12]
    h = head(title, desc, path, [cld, faq_ld])
    h += f"""
  <main id="main" class="wrap">
    {ch}
    <div class="page-split"><header class="page-head">
      <ul class="pills"><li>{E(g['group'])}</li><li>{E(g['label'])}</li></ul>
      <h1>{E(short)}: the <span class="hl">{p}% cheaper</span> generic</h1>
      <p class="lead">{E(b['name'])} by {E(short_mfr(b['mfr']))} contains <b>{E(g['label'])}</b>. The Jan Aushadhi generic with the same salt costs {rs(g['per_unit'])} per {form} instead of {rs(b['per_unit'])}.</p>
      <p class="hand">same salt, same strength ✓</p>
    </header>
    {compare_card(b, g, static=True, path=path)}</div>
    <div class="prose">
      <h2>Other brands with the same salt</h2>
      <p class="muted">All contain {E(g['label'])} ({form}).</p>
    </div>
    {brand_table(g, others, 12)}
    <p style="margin-top:14px"><a class="btn btn-ghost" href="{BASE}/medicine/{g['slug']}/">All {len(g['brands'])} brands of {E(g['label'])} →</a></p>
    <div class="prose"><h2>Questions</h2>{faq_html}{disclaimer()}</div>
  </main>
"""
    write(f"brand/{b['slug']}/index.html", h + FOOT)

def build_medicines_index():
    groups = collections.defaultdict(list)
    for g in gens: groups[g["group"]].append(g)
    cld, ch = crumbs([("Home", "/"), ("Medicines", "/medicines/")])
    body = ""
    for grp in sorted(groups, key=lambda k: -len(groups[k])):
        items = sorted(groups[grp], key=lambda g: g["label"])
        body += f'<h2 id="{slugify(grp)}">{E(grp)} <small class="muted">({len(items)})</small></h2><div class="links-cloud">' + \
                "".join(f'<a class="chip" href="{BASE}/medicine/{g["slug"]}/">{E(g["label"])} {g["form"]}</a>' for g in items) + "</div>"
    h = head(f"All {len(gens)} Jan Aushadhi Medicines with Brand Price Comparison | {NAME}",
             f"Browse {len(gens)} Jan Aushadhi generic tablets and capsules by therapeutic group, each compared with the branded medicines that contain the same salt.",
             "/medicines/", [cld])
    h += f"""<main id="main" class="wrap">{ch}<header class="page-head"><h1>All medicines</h1>
<p class="lead">{len(gens)} Jan Aushadhi tablets and capsules that we could match to branded medicines, grouped the way PMBI groups them.</p></header>
<div class="prose" style="max-width:none">{body}</div></main>"""
    write("medicines/index.html", h + FOOT)

# stores ---------------------------------------------------------------
by_state = collections.defaultdict(lambda: collections.defaultdict(list))
for s in stores: by_state[s["state"]][s["district"]].append(s)

def popular_cities_html():
    top = sorted(((st, d, len(v)) for st, ds in by_state.items() for d, v in ds.items()), key=lambda x: -x[2])[:14]
    return "".join(f'<a class="chip" href="{BASE}/stores/{slugify(st)}/{slugify(d)}/">{E(d)} <small class="muted">{n}</small></a>' for st, d, n in top)

def store_li(s):
    dirl = f'https://www.google.com/maps/dir/?api=1&destination={s["lat"]},{s["lng"]}' if s["lat"] else f'https://www.google.com/maps/search/?api=1&query={html.escape(s["addr"] + " " + str(s["pin"]))}'
    return (f'<li class="store"><b>Jan Aushadhi Kendra {E(s["code"])}</b><div class="meta">{E(s["district"])}, {E(s["state"])} · PIN {s["pin"]}</div>'
            f'{E(s["addr"])}<br><a href="{dirl}" target="_blank" rel="noopener" data-track="store_directions">Get directions →</a></li>')

def build_stores():
    leaflet = ('\n  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">'
               '\n  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" defer></script>'
               f'\n  <script src="{BASE}/assets/stores.js" defer></script>')
    cld, ch = crumbs([("Home", "/"), ("Find a Kendra", "/stores/")])
    states = sorted(by_state, key=lambda st: -sum(len(v) for v in by_state[st].values()))
    st_html = "".join(f'<a class="chip" href="{BASE}/stores/{slugify(st)}/">{E(st)} <small class="muted">{sum(len(v) for v in by_state[st].values())}</small></a>' for st in states)
    h = head(f"Jan Aushadhi Kendra Near Me: {len(kendras):,} Stores on a Map | {NAME}",
             f"Find the nearest Jan Aushadhi Kendra by location or PIN code. {len(kendras):,} Pradhan Mantri Bhartiya Janaushadhi Kendras on a map, with directions.",
             "/stores/", [cld], leaflet)
    h += f"""<main id="main" class="wrap">{ch}
<header class="page-head"><h1>Find a Jan Aushadhi Kendra near you</h1>
<p class="lead">{len(kendras):,} Kendras from the official PMBI list. Use your location, or type a PIN code.</p></header>
<div class="store-tools">
  <button id="use-loc" class="btn btn-leaf" type="button">{I['loc']}Use my location</button>
  <form id="pin-form" style="display:flex;gap:8px"><label class="skip" for="pin">PIN code</label><input id="pin" inputmode="numeric" maxlength="6" placeholder="PIN code, e.g. 211012"><button class="btn btn-ghost" type="submit">Search</button></form>
</div>
<p id="store-msg" class="status-msg" aria-live="polite">Your location is used only in your browser to sort stores by distance.</p>
<div class="store-layout"><div id="map" role="region" aria-label="Map of Jan Aushadhi Kendras"></div><ul id="store-list" class="store-list"></ul></div>
<div class="prose" style="max-width:none"><h2>Browse by state</h2><div class="links-cloud">{st_html}</div></div>
</main>"""
    write("stores/index.html", h + FOOT)
    for st in states:
        ds = by_state[st]
        total = sum(len(v) for v in ds.values())
        cld, ch = crumbs([("Home", "/"), ("Find a Kendra", "/stores/"), (st, f"/stores/{slugify(st)}/")])
        dl = "".join(f'<a class="chip" href="{BASE}/stores/{slugify(st)}/{slugify(d)}/">{E(d)} <small class="muted">{len(v)}</small></a>'
                     for d, v in sorted(ds.items(), key=lambda x: -len(x[1])))
        h = head(f"Jan Aushadhi Kendras in {st}: {total:,} Stores by District | {NAME}",
                 f"List of {total:,} Jan Aushadhi Kendras in {st} across {len(ds)} districts, with addresses and directions.",
                 f"/stores/{slugify(st)}/", [cld])
        h += f"""<main id="main" class="wrap">{ch}<header class="page-head"><h1>Jan Aushadhi Kendras in {E(st)}</h1>
<p class="lead">{total:,} Kendras across {len(ds)} districts. Pick a district to see addresses and directions.</p></header>
<div class="links-cloud">{dl}</div></main>"""
        write(f"stores/{slugify(st)}/index.html", h + FOOT)
        for d, v in ds.items():
            path = f"/stores/{slugify(st)}/{slugify(d)}/"
            cld, ch = crumbs([("Home", "/"), ("Find a Kendra", "/stores/"), (st, f"/stores/{slugify(st)}/"), (d, path)])
            v = sorted(v, key=lambda s: (s["pin"], s["code"]))
            pins = sorted({s["pin"] for s in v if s["pin"]})
            list_ld = {"@context": "https://schema.org", "@type": "ItemList", "name": f"Jan Aushadhi Kendras in {d}", "numberOfItems": len(v),
                       "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": {"@type": "Pharmacy", "name": f"Jan Aushadhi Kendra {s['code']}",
                           "address": {"@type": "PostalAddress", "streetAddress": s["addr"], "addressLocality": d, "addressRegion": st, "postalCode": str(s["pin"]), "addressCountry": "IN"},
                           **({"geo": {"@type": "GeoCoordinates", "latitude": s["lat"], "longitude": s["lng"]}} if s["lat"] else {})}} for i, s in enumerate(v[:100])]}
            h = head(f"Jan Aushadhi Kendra in {d}: {len(v)} Stores with Address & Directions",
                     f"{len(v)} Jan Aushadhi Kendras in {d}, {st}" + (f" (PIN {pins[0]}–{pins[-1]})" if len(pins) > 1 else "") + ". Addresses, PIN codes and Google Maps directions.",
                     path, [cld, list_ld])
            h += f"""<main id="main" class="wrap">{ch}<header class="page-head"><h1>Jan Aushadhi Kendras in {E(d)}</h1>
<p class="lead">{len(v)} Kendra{'s' if len(v) != 1 else ''} in {E(d)}, {E(st)}. For the ones closest to you, use the <a href="{BASE}/stores/">map with your location</a>.</p></header>
<ul class="store-list" style="max-height:none;grid-template-columns:repeat(auto-fill,minmax(300px,1fr))">{''.join(store_li(s) for s in v)}</ul>
<div class="prose">{disclaimer()}</div></main>"""
            write(f"stores/{slugify(st)}/{slugify(d)}/index.html", h + FOOT)

def build_about():
    cld, ch = crumbs([("Home", "/"), ("How it works", "/about/")])
    unmatched = len(products) - len(gens)
    h = head(f"How {NAME} Works: Data Sources, Matching Method and Limits",
             "How Generic Bachat matches branded medicines to Jan Aushadhi generics by salt, strength and dosage form, where the prices come from, and what it can't do.",
             "/about/", [cld])
    h += f"""<main id="main" class="wrap">{ch}<article class="prose">
<header class="page-head"><h1>How Generic Bachat works</h1>
<p class="lead">India's Jan Aushadhi scheme sells generic medicines for a fraction of brand prices, but few people know which generic replaces the brand on their prescription. This site answers that one question, honestly.</p></header>
<h2>Data sources</h2>
<ul>
<li><b>Jan Aushadhi products and MRPs:</b> the official product list published by PMBI (Pharmaceuticals &amp; Medical Devices Bureau of India) on janaushadhi.gov.in. {len(products):,} products, fetched {DATA_DATE}.</li>
<li><b>Jan Aushadhi Kendras:</b> the official store list from the same site: {len(kendras):,} Kendras with addresses, PIN codes and map coordinates.</li>
<li><b>Brand prices and compositions:</b> the open <a href="https://github.com/junioralive/Indian-Medicine-Dataset" rel="noopener">Indian Medicine Dataset</a> (MIT licence), compiled from public online-pharmacy listings. Brand MRPs change, so treat them as indicative.</li>
</ul>
<h2>How a brand is matched to a generic</h2>
<ol>
<li>Each Jan Aushadhi name (for example “Pantoprazole Gastro Resistant Tablets IP 40 mg”) is parsed into its salts and strengths, and its dosage form (tablet or capsule).</li>
<li>Salt names are normalised: “Amoxycillin” = “Amoxicillin”, and counter-ions are dropped (“Metformin Hydrochloride” = “Metformin”). Strengths are converted to the same unit (500 mcg = 0.5 mg).</li>
<li>Sustained-release products are only matched with sustained-release products, never with normal tablets.</li>
<li>A brand matches only if <b>every</b> salt and strength is identical.</li>
<li>The brand dataset records at most two ingredients, so a three-ingredient brand could look like a two-ingredient one. To avoid that, two-ingredient brands are skipped when their name carries a marker that, in the data, almost always means a third ingredient (for example “SP”, “Trio”, “Gold”, “AMH”), when their name shows three strengths, or when the same maker sells a shorter-named brand with the same recorded composition (Telma-AM vs Telma-AM-H).</li>
<li>Prices are compared <b>per tablet or capsule</b>, so different pack sizes are fair.</li>
</ol>
<p>Result: {len(gens)} Jan Aushadhi tablets and capsules matched to {n_brands:,} branded products. The median brand costs {median_saving}% more than its Jan Aushadhi equivalent.</p>
<h2>Limits</h2>
<ul>
<li>Syrups, injections, creams and devices are not compared yet ({unmatched:,} Jan Aushadhi products), because their pack sizes are hard to compare fairly.</li>
<li>Availability varies by Kendra. Call or visit before you travel.</li>
<li>Some brands differ in coating or release type, or contain an extra ingredient, in ways the data doesn't show. The composition printed on the pack is the final word; every result tells you exactly what it should say.</li>
</ul>
{disclaimer()}
<h2>Who made this</h2>
<p>Generic Bachat is an independent project by <a href="https://chinmaya2310.github.io/?utm_source=generic_bachat&utm_medium=referral&utm_campaign=about">Chinmaya Kumar Nayak</a>, an M.Tech student at IIIT Allahabad. It is not affiliated with PMBI or the Government of India, and it earns nothing from any sale. Found a wrong match? Email <a href="mailto:chinmayanayak018@gmail.com?subject=Generic%20Bachat%20correction">chinmayanayak018@gmail.com</a>.</p>
</article></main>"""
    write("about/index.html", h + FOOT)

def build_404():
    h = head(f"Page not found | {NAME}", "This page doesn't exist.", "/404.html", robots="noindex")
    h = h.replace(f'href="{BASE}/assets', f'href="{BASE}/assets')
    h += f"""<main id="main" class="wrap"><section class="hero"><h1>Page not found</h1>
<p class="lead">Search for your medicine instead:</p><a class="btn" href="{BASE}/">Go to search</a></section></main>"""
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
