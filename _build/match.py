"""Match branded Indian medicines to Jan Aushadhi generics by (salts, strengths, dosage form).

Inputs : ja/products.json (PMBI official list), azdata/meds.csv (brand MRPs, MIT dataset)
Output : out/data.json used by the site generator
"""
import csv, json, re, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.path.dirname(HERE), "_data", "raw")
OUT = os.path.join(os.path.dirname(HERE), "_data"); os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- normalisation
SYN = {
    "amoxycillin": "amoxicillin", "acetaminophen": "paracetamol", "clavulanate": "clavulanic acid",
    "potassium clavulanate": "clavulanic acid", "diluted potassium clavulanate": "clavulanic acid",
    "cephalexin": "cefalexin", "frusemide": "furosemide", "glibenclamide": "glyburide",
    "salbutamol": "salbutamol", "albuterol": "salbutamol", "levocetirizine": "levocetirizine",
    "cholecalciferol": "vitamin d3", "vitamin d3": "vitamin d3", "ascorbic acid": "vitamin c",
    "methylcobalamin": "methylcobalamin", "mecobalamin": "methylcobalamin", "ofloxacin": "ofloxacin",
    "rabeprazole": "rabeprazole", "esomeprazole": "esomeprazole", "dicyclomine": "dicyclomine",
    "dicycloverine": "dicyclomine", "telmisartan": "telmisartan", "chlorthalidone": "chlortalidone",
    "chlortalidone": "chlortalidone", "aceclofenac": "aceclofenac", "drotaverine": "drotaverine",
    "ondansetron": "ondansetron", "domperidone": "domperidone", "glimepride": "glimepiride",
    "metformin": "metformin", "voglibose": "voglibose", "sitagliptin": "sitagliptin",
    "vildagliptin": "vildagliptin", "teneligliptin": "teneligliptin", "dapagliflozin": "dapagliflozin",
    "empagliflozin": "empagliflozin", "clopidogrel": "clopidogrel", "aspirin": "aspirin",
    "acetylsalicylic acid": "aspirin", "amlodipine": "amlodipine", "atenolol": "atenolol",
    "ferrous ascorbate": "ferrous ascorbate", "folic acid": "folic acid", "thyroxine": "levothyroxine",
    "levothyroxine": "levothyroxine", "montelukast": "montelukast", "fexofenadine": "fexofenadine",
    "azithromycin": "azithromycin", "cefixime": "cefixime", "cefpodoxime proxetil": "cefpodoxime",
    "cefuroxime axetil": "cefuroxime", "itopride": "itopride", "levosulpiride": "levosulpiride",
    "ursodeoxycholic acid": "ursodeoxycholic acid", "ursodiol": "ursodeoxycholic acid",
    "diclofenac": "diclofenac", "serratiopeptidase": "serratiopeptidase", "trypsin chymotrypsin": "trypsin chymotrypsin",
    "nimesulide": "nimesulide", "ibuprofen": "ibuprofen", "mefenamic acid": "mefenamic acid",
    "tramadol": "tramadol", "pregabalin": "pregabalin", "gabapentin": "gabapentin",
    "nortriptyline": "nortriptyline", "escitalopram": "escitalopram", "clonazepam": "clonazepam",
    "etizolam": "etizolam", "alprazolam": "alprazolam", "olmesartan medoxomil": "olmesartan",
    "losartan": "losartan", "rosuvastatin": "rosuvastatin", "atorvastatin": "atorvastatin",
    "fenofibrate": "fenofibrate", "metoprolol succinate": "metoprolol succinate",
    "metoprolol tartrate": "metoprolol tartrate", "metoprolol": "metoprolol",
    "torsemide": "torasemide", "torasemide": "torasemide", "spironolactone": "spironolactone",
    "hydrochlorothiazide": "hydrochlorothiazide", "ramipril": "ramipril", "cilnidipine": "cilnidipine",
    "bisoprolol": "bisoprolol", "nebivolol": "nebivolol", "prasugrel": "prasugrel", "ticagrelor": "ticagrelor",
    "sodium valproate": "valproate", "valproic acid": "valproate", "divalproex": "valproate",
    "levetiracetam": "levetiracetam", "phenytoin": "phenytoin", "carbamazepine": "carbamazepine",
    "oxcarbazepine": "oxcarbazepine", "lamotrigine": "lamotrigine",
}
# counter-ions / pharmacopoeia tags stripped from the END of a salt name ("metformin hydrochloride" -> "metformin")
TRAIL = set("""hydrochloride dihydrochloride hcl hydrobromide sodium potassium calcium magnesium besylate besilate maleate
mesylate mesilate fumarate citrate sulphate sulfate phosphate acetate dihydrate monohydrate trihydrate hemihydrate
sesquihydrate anhydrous bitartrate bromide dipropionate propionate furoate xinafoate disodium tromethamine hyclate
axetil proxetil medoxomil ip bp usp ep orodispersible""".split())

def norm_salt(s):
    s = s.lower()
    s = s.split("/")[0]                       # "paracetamol/acetaminophen" -> "paracetamol"
    s = re.sub(r"\(.*?\)", " ", s)
    m = re.search(r"metoprolol\s+(succinate|tartrate)", s)
    if m: return "metoprolol " + m.group(1)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\b(diluted|equivalent to|eq to|as)\b", " ", s)
    toks = s.split()
    while len(toks) > 1 and toks[-1] in TRAIL: toks.pop()
    while len(toks) > 1 and toks[0] in ("ip", "bp", "usp"): toks.pop(0)
    s = " ".join(toks)
    return SYN.get(s, s)

def norm_strength(num, unit):
    v = float(num); u = unit.lower().replace("µ", "mc")
    if u in ("g", "gm", "gram"): v, u = v * 1000, "mg"
    elif u in ("mcg", "ug"): v, u = v / 1000, "mg"
    elif u in ("iu",): u = "iu"
    elif u == "%": u = "%"
    else: u = "mg"
    return f"{round(v, 4):g}{u}"

# ---------------------------------------------------------------- dosage forms
def form_of(text):
    t = text.lower()
    if re.search(r"\b(tablets?|tab)\b", t): return "tablet"
    if re.search(r"\b(capsules?|cap|softgels?)\b", t): return "capsule"
    return None

REL = re.compile(r"\b(sr|er|xr|cr|pr|mr|xl|cd|la|retard|sustained|prolonged|extended|controlled|modified)\b", re.I)
def release(text):
    return "mr" if REL.search(text.replace("-", " ")) else "ir"

# ---------------------------------------------------------------- Jan Aushadhi parsing
JA_NOISE = r"\b(tablets?|capsules?|ip|bp|usp|film[- ]coated|enteric[- ]coated|gastro[- ]?resistant|gastro[- ]?resistance|sustained[- ]release|prolonged[- ]release|extended[- ]release|modified[- ]release|controlled[- ]release|delayed[- ]release|immediate[- ]release|dispersible|chewable|uncoated|orally disintegrating|mouth dissolving|hard gelatin|soft gelatin|sr|er|xr|cr|mr|dr|od|oral|each|contains|containing|tablet|capsule|equivalent|eq\.?|to|of|anhydrous|as|in|bilayered|bilayer|coated|pellets?|orodispersible|ir)\b"

STR = r"(\d+(?:\.\d+)?)\s*(mg|mcg|µg|g|gm|iu|%)\b"

PAIR = re.compile(r"([a-z][a-z\-\s\.]*?)\s*" + STR, re.I)

def parse_ja(name):
    form = form_of(name)
    if not form: return None
    t = name.replace("+", " ").replace(",", " ").replace(";", " ")
    t = re.sub(r"per\s*\d+\s*ml", " ", t, flags=re.I)
    t = re.sub(r"\((?![^)]*\d)[^)]*\)", " ", t)      # drop "(Enteric Coated)", keep "(40 mg)"
    t = t.replace("(", " ").replace(")", " ")
    t = re.sub(JA_NOISE, " ", t, flags=re.I)
    t = re.sub(r"\b(and|with)\b", " ", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    comps, pos = [], 0
    for m in PAIR.finditer(t):
        salt = m.group(1).strip()
        if not re.search(r"[a-z]{3,}", salt, re.I): return None
        comps.append((norm_salt(salt), norm_strength(m.group(2), m.group(3))))
        pos = m.end()
    if not comps or re.search(r"[a-z]{3,}", t[pos:], re.I): return None
    if len({c[0] for c in comps}) != len(comps) or any(not c[0] for c in comps): return None
    return form, tuple(sorted(comps))

def units_ja(unit_size):
    m = re.match(r"\s*(\d+)\s*'?s\b", unit_size.lower())
    return int(m.group(1)) if m else None

# ---------------------------------------------------------------- brand parsing
def parse_comp(c):
    c = c.strip()
    if not c: return None
    m = re.match(r"(.+?)\s*\(\s*" + STR + r"\s*\)", c, re.I)
    if not m: return "BAD"
    return norm_salt(m.group(1)), norm_strength(m.group(2), m.group(3))

def units_brand(pack):
    m = re.match(r"\s*(strip|bottle|box|pack|blister|tube|packet|jar)? ?of (\d+) (tablets?|capsules?|soft gelatin capsules?)", pack.lower())
    return int(m.group(2)) if m else None

# Learned from the dataset: tokens far more common in names with 3 strengths ("100/325/15") than with 2.
THIRD = re.compile(r"\b(trio|triple|tri\w*|gold|total|quad|4in1|3in1|sp|mp|mv|pm|cold|br|vg|amh|ah|ps|mnt|vm|msm|gv|pth|aps|joint)\b", re.I)
FORMWORDS = set("tablet tablets capsule capsules sr pr er xr cr mr dt od ds md soft gelatin kid kids".split())
def stem(name):
    toks = re.findall(r"[a-z]+", name.lower())
    return tuple(t for t in toks if t not in FORMWORDS)

# ---------------------------------------------------------------- run
def main():
    ja = json.load(open(os.path.join(RAW, "products.json")))["responseBody"]["newProductResponsesList"]
    gen = {}
    unparsed = 0
    for p in ja:
        if p["mrp"] <= 0: continue
        r = parse_ja(p["genericName"])
        n = units_ja(p["unitSize"])
        if not r or not n:
            unparsed += 1; continue
        form, comps = r
        key = (form, release(p["genericName"]), comps)
        per_unit = p["mrp"] / n
        cur = gen.get(key)
        if cur is None or per_unit < cur["per_unit"]:
            gen[key] = {"drug_code": p["drugCode"], "name": p["genericName"].strip(), "group": p["groupName"],
                        "unit_size": p["unitSize"], "mrp": p["mrp"], "units": n, "per_unit": per_unit,
                        "form": form, "release": key[1], "comps": comps}
    print(f"JA tablets/capsules parsed: {len(gen)} keys (unparsed/other forms: {unparsed})", file=sys.stderr)

    brands = collections.defaultdict(list)
    bad = 0
    # the dataset is ordered A-Z, most popular first within each starting letter,
    # so "position within its letter" is a usable popularity rank
    first_id = {}
    with open(os.path.join(RAW, "meds.csv"), newline="") as f:
        for row in csv.DictReader(f):
            first_id.setdefault(row["name"][:1].lower(), int(row["id"]))
    with open(os.path.join(RAW, "meds.csv"), newline="") as f:
        for row in csv.DictReader(f):
            if row["Is_discontinued"].upper() == "TRUE": continue
            try: price = float(row["price(₹)"])
            except ValueError: continue
            form = form_of(row["pack_size_label"]) or form_of(row["name"])
            n = units_brand(row["pack_size_label"])
            if not form or not n or price <= 0: continue
            cs = [parse_comp(row["short_composition1"]), parse_comp(row["short_composition2"])]
            if "BAD" in cs: bad += 1; continue
            comps = tuple(sorted(c for c in cs if c))
            if not comps: continue
            # dataset keeps only 2 compositions: skip brands whose name shows more strengths ("75mg/10mg/1500mcg")
            sm = re.search(r"\d[\d.]*\s*(?:mg|mcg|g|iu)?(?:\s*/\s*\d[\d.]*\s*(?:mg|mcg|g|iu)?)+", row["name"], re.I)
            if sm and len(re.findall(r"\d[\d.]*", sm.group(0))) != len(comps): continue
            if len(comps) == 2 and re.search(r"\b(plus|forte|trio|triple)\b", row["name"], re.I) and not sm: pass
            # brand forms: treat "capsule" vs "tablet" separately, as Jan Aushadhi does
            key = (form, release(row["name"]), comps)
            # names that usually signal a 3rd ingredient the dataset dropped
            if len(comps) == 2 and THIRD.search(row["name"]): continue
            if key in gen:
                brands[key].append({"id": int(row["id"]), "rank": int(row["id"]) - first_id[row["name"][:1].lower()], "name": row["name"].strip(), "mfr": row["manufacturer_name"].strip(),
                                    "price": price, "units": n, "pack": row["pack_size_label"].strip(), "ncomp": len(comps)})
    print(f"brand rows with bad composition: {bad}", file=sys.stderr)

    # Same maker, same recorded 2-salt composition, different brand stems (Telma-AM vs Telma-AM-H):
    # the extra-suffix names usually hide a 3rd ingredient, so keep only the shortest stem(s).
    dropped = 0
    for key, bl in brands.items():
        if len(key[2]) != 2: continue
        by_mfr = collections.defaultdict(list)
        for b in bl: by_mfr[b["mfr"].lower()].append(b)
        keep_ids = set()
        for mb in by_mfr.values():
            stems = {}
            for b in mb: stems.setdefault(stem(b["name"]), []).append(b)
            # drop a stem only if it extends another stem from the same maker (telma am -> telma am h)
            for st, group in stems.items():
                extends = any(o != st and len(o) < len(st) and st[:len(o)] == o for o in stems)
                if not extends: keep_ids.update(id(b) for b in group)
        before = len(bl)
        bl[:] = [b for b in bl if id(b) in keep_ids]
        dropped += before - len(bl)
    print(f"dropped as possible hidden 3rd ingredient: {dropped}", file=sys.stderr)

    out = []
    for key, g in gen.items():
        bl = brands.get(key, [])
        if not bl: continue
        for b in bl:
            b["per_unit"] = b["price"] / b["units"]
        bl.sort(key=lambda b: b["rank"])
        out.append({**g, "comps": [list(c) for c in g["comps"]], "brands": bl})
    out.sort(key=lambda g: min(b["rank"] for b in g["brands"]))
    nb = sum(len(g["brands"]) for g in out)
    print(f"matched generics: {len(out)}, brands mapped: {nb}", file=sys.stderr)
    json.dump(out, open(os.path.join(OUT, "matched.json"), "w"))

if __name__ == "__main__":
    main()
