#!/usr/bin/env python3
"""
KEPT — catalogue engine
=======================
Pulls live product data straight from New Zealand retailers' own storefronts and
writes it to products.json, which the app reads on load.

Most NZ fashion retailers run on Shopify, which publishes a public JSON feed at
    https://{store}/products.json?limit=250&page=N
This script walks that feed for every store in STORES, cleans and categorises
each product, flags New Zealand-designed labels, and writes a single file.

Run locally:      python3 scripts/fetch_products.py
Run in CI:        see .github/workflows/refresh-catalogue.yml (runs daily)
"""

import json, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

# ---------------------------------------------------------------- stores
# (domain, display name, max pages to walk)
# Add a new NZ retailer by appending one line. If it runs on Shopify it just works.
STORES = [
    # ---- already live ----
    ("kowtowclothing.com",            "Kowtow",                 12),
    ("www.superette.co.nz",           "Superette",              25),
    ("karenwalker.com",               "Karen Walker",           15),
    ("www.rubynz.com",                "Ruby",                   20),
    ("www.deadlyponies.com",          "Deadly Ponies",          10),
    ("www.standardissue.co.nz",       "Standard Issue",         10),
    ("maggiemarilyn.com",             "Maggie Marilyn",          8),
    ("twentysevennames.co.nz",        "twenty-seven names",      8),
    ("www.stolengirlfriendsclub.com", "Stolen Girlfriends Club", 8),
    ("juliettehogan.com",             "Juliette Hogan",         12),
    ("www.moochi.co.nz",              "Moochi",                 12),
    ("www.companyofstrangers.co.nz",  "Company of Strangers",    8),
    ("yumeibrand.com",                "Yu Mei",                  8),
    ("www.commoners.co.nz",           "Commoners",              10),
    ("katesylvester.com",             "Kate Sylvester",         10),
    ("saben.co.nz",                   "Saben",                   8),
    ("caitlincrisp.com",              "Caitlin Crisp",           8),
    ("harristapper.com",              "Harris Tapper",           8),
    ("pennysage.com",                 "Penny Sage",              8),
    ("zambesistore.com",              "Zambesi",                10),
    ("huffer.co.nz",                  "Huffer",                 15),
    ("www.untouchedworld.com",        "Untouched World",        12),
    ("georgiajay.com",                "Georgia Jay",             6),
    ("www.mipiaci.co.nz",             "Mi Piaci",               12),
    ("www.merchant1948.co.nz",        "Merchant 1948",          12),
    ("meadowlarkjewellery.com",       "Meadowlark",             10),
    ("salasai.com",                   "Salasai",                 6),
    ("recreateclothing.co.nz",        "ReCreate",                6),
    ("www.nyne.co.nz",                "Nyne",                    6),
    ("zoeandmorgan.com",              "Zoe & Morgan",           10),
    ("www.workshop.co.nz",            "Workshop",               20),

    # ---- new: designers & boutiques ----
    ("wynnhamlyn.com",                "Wynn Hamlyn",             8),
    ("parisgeorgia.com",              "Paris Georgia",           6),
    ("ingridstarnes.com",             "Ingrid Starnes",          8),
    ("nomd.co.nz",                    "Nom*D",                   8),
    ("www.taylorboutique.co.nz",      "Taylor",                 10),
    ("www.widdess.com",               "Widdess",                 6),
    ("maaike.co.nz",                  "Maaike",                  6),
    ("ketzke.com",                    "Ketzke",                  6),
    ("lonelylabel.com",               "Lonely",                 10),
    ("kilt.co.nz",                    "Kilt",                   10),
    ("www.federationclothing.com",    "Federation",             10),
    ("augustine.co.nz",               "Augustine",              10),
    ("www.trelisecooper.co.nz",       "Trelise Cooper",         12),
    ("www.annahstretton.co.nz",       "Annah Stretton",         10),
    ("www.sillsandco.co.nz",          "Sills & Co",              8),
    ("theshelter.co.nz",              "The Shelter",            10),
    ("www.muse-boutique.co.nz",       "Muse Boutique",          10),
    ("www.repertoirefashion.co.nz",   "Repertoire",             12),
    ("www.blackboxboutique.co.nz",    "Black Box Boutique",     10),
    ("www.hartleys.co.nz",            "Hartleys",               10),
    ("www.gregorywomenswear.com",     "Gregory",                 8),
    ("crane-brothers.com",            "Crane Brothers",         10),
    ("www.barkers.co.nz",             "Barkers",                12),
    ("paperplanestore.com",           "Paper Plane",            12),

    # ---- new: shoes, bags & jewellery ----
    ("chaosandharmony.com",           "Chaos & Harmony",         8),
    ("kathrynwilsonfootwear.com",     "Kathryn Wilson",         10),
    ("www.overland.co.nz",            "Overland",               12),
    ("www.minxshoes.co.nz",           "Minx",                   10),
    ("naveyaandsloane.com",           "Naveya & Sloane",         8),
    ("www.walkerandhall.co.nz",       "Walker & Hall",          10),
    ("www.stolen.co.nz",              "Stolen",                  6),
]

# ---------------------------------------------------------------- NZ labels
NZ_TOKENS = (
    'kowtow','karen walker','ruby','liam','deadly ponies','standard issue','forever',
    'maggie marilyn','twenty-seven','twentyseven','stolen girlfriends','juliette hogan',
    'moochi','6&7','company of strangers','james brown','yu mei','commoners','sylvester',
    'saben','caitlin crisp','harris tapper','penny sage','fairley','pinky and kamal',
    'zambesi','huffer','untouched world','georgia jay','mi piaci','merchant 1948',
    'isabella anselmi','deuce','field & foundry','meadowlark','salasai','recreate','nyne',
    'zoe & morgan','kate sylvester','widdess','wynn hamlyn','paris georgia','ingrid starnes',
    'jimmy d','turet','nom d','twenty seven names','okewa','ovna ovich','georgia alice',
)

IMG_OK   = re.compile(r'\.(jpe?g|png|webp)(\?|$)', re.I)
JUNK     = ('gift card','giftcard','gift-card','e-gift','lookbook','sample','deposit',
            'test product','content tile','collection content','care kit','protector',
            'gift voucher','voucher','shipping','donation','afterpay','gwp','goodie bag',
            'repair','alteration','swatch')

UA = {'User-Agent': 'Mozilla/5.0 (compatible; KeptCatalogue/1.0; +https://kept.nz)'}


def categorise(ptype: str, title: str) -> str:
    s = f"{ptype} {title}".lower()
    def has(*w): return any(x in s for x in w)
    if has('sunglass', 'eyewear'):                                   return 'Accessories'
    if has('earring','necklace','bracelet','huggie','hoop','stud','sleeper',
           'jewellery','jewelry','pendant','anklet','signet',' ring','rings'): return 'Jewellery'
    if has('bag','tote','clutch','crossbody','pouch','sling','backpack','wallet',
           'cardholder','purse','satchel','hobo','shoulder bag'):    return 'Bags'
    if has('shoe','footwear','sneaker','boot','loafer','ballet flat','sandal','heel',
           'welly','mule','clog','slide','slingback','wedge','thong','flats','trainer'): return 'Shoes'
    if has('dress','gown','jumpsuit','sundress','tunic'):            return 'Dresses'
    if has('skirt'):                                                 return 'Skirts'
    if has('coat','trench','parka','anorak','puffer','jacket','blazer','bomber',
           'vest','gilet','shacket','outerwear'):                    return 'Outerwear'
    if has('knit','sweater','jumper','cardigan','cardi','pullover','jersey','hoodie',
           'hood','sweatshirt','sweat','fleece','merino','cashmere'):return 'Knitwear'
    if has('pant','trouser','jean','denim','short','dungaree','legging','chino'): return 'Bottoms'
    if has('shirt','tee','t-shirt','top','blouse','tank','polo','cami','bodysuit',
           'body suit','singlet','bodice','sleeve'):                 return 'Tops'
    if has('scarf','belt','hat','cap','beanie','glove','sock','wrap','charm','key'): return 'Accessories'
    return ''


def is_nz(*fields) -> bool:
    blob = ' '.join(f.lower() for f in fields if f)
    return any(tok in blob for tok in NZ_TOKENS)


def tidy_brand(vendor: str, fallback: str) -> str:
    v = (vendor or '').strip()
    if not v or v in {'0', '-'}:
        return fallback
    if v.isupper() and len(v) > 3:
        v = v.title()
    return {'Ruby': 'RUBY', 'Company': 'Company of Strangers'}.get(v, v)


def get_json(url: str, tries: int = 2):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=12) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as e:
            if attempt == tries - 1:
                print(f"    ! {type(e).__name__}: {url}")
                return None
            time.sleep(1.0)
    return None


def harvest(domain: str, label: str, max_pages: int):
    out = []
    # some stores hide the root feed but expose /collections/all
    base = f"https://{domain}/products.json"
    if not ((get_json(base + "?limit=1") or {}).get('products')):
        alt = f"https://{domain}/collections/all/products.json"
        if ((get_json(alt + "?limit=1") or {}).get('products')):
            base = alt
        else:
            return out
    for page in range(1, max_pages + 1):
        url = f"{base}?limit=250&page={page}"
        data = get_json(url)
        products = (data or {}).get('products') or []
        if not products:
            break
        for p in products:
            title  = (p.get('title') or '').strip()
            handle = (p.get('handle') or '').strip()
            ptype  = (p.get('product_type') or '').strip()
            vendor = (p.get('vendor') or '').strip()
            if not title or not handle:
                continue

            low = f"{title} {handle} {ptype}".lower()
            if any(j in low for j in JUNK):
                continue

            variants = p.get('variants') or []
            avail = [v for v in variants if v.get('available')]
            pick = (avail or variants or [{}])[0]
            try:
                price = float(str(pick.get('price') or 0).replace('$', '').replace(',', ''))
            except ValueError:
                price = 0.0
            if price < 15:                       # placeholders / lookbook entries
                continue

            images = p.get('images') or []
            img = next((i.get('src') for i in images
                        if i.get('src') and IMG_OK.search(i['src']) and 'eyJ' not in i['src']), None)
            if not img:
                continue

            cat = categorise(ptype, title)
            if not cat:
                continue

            brand = tidy_brand(vendor, label)
            out.append({
                'title': re.sub(r'\s+', ' ', title)[:90],
                'brand': brand,
                'store': label,
                'cat':   cat,
                'price': int(round(price)),
                'img':   img,
                'url':   f"https://{domain}/products/{handle}",
                'nz':    is_nz(brand, label, domain),
                'stock': bool(avail) or None,
            })
        if len(products) < 250:
            break
        time.sleep(0.4)                          # be a polite guest
    return out


def main():
    # Optional batching so a slow store can never stall the whole run:
    #   python3 scripts/fetch_products.py --slice 0:6 --out parts/p0.json
    #   python3 scripts/fetch_products.py --merge parts
    args = sys.argv[1:]
    if '--merge' in args:
        return merge(args[args.index('--merge') + 1])
    stores = STORES
    out_path = 'products.json'
    if '--slice' in args:
        a, b = args[args.index('--slice') + 1].split(':')
        stores = STORES[int(a):int(b)]
    if '--out' in args:
        out_path = args[args.index('--out') + 1]

    all_items, per_store, failed = [], {}, []
    for domain, label, pages in stores:
        print(f"→ {label} ({domain})")
        try:
            items = harvest(domain, label, pages)
        except Exception as e:
            print(f"    ! failed: {e}")
            items = []
        if not items:
            failed.append(label)
        per_store[label] = len(items)
        all_items.extend(items)
        print(f"    {len(items)} items")

    write_payload(all_items, per_store, failed, out_path)


def write_payload(all_items, per_store, failed, out_path='products.json', guard=True):
    # de-duplicate on image, then on store+title
    seen_img, seen_key, deduped = set(), set(), []
    for it in all_items:
        ik = it['img'].split('?')[0]
        tk = (it['store'], it['title'].lower(), it['price'])
        if ik in seen_img or tk in seen_key:
            continue
        seen_img.add(ik); seen_key.add(tk)
        it.pop('stock', None)
        deduped.append(it)

    # NZ-designed first, then spread brands so one label never floods the deck
    deduped.sort(key=lambda x: (not x['nz'], hash(x['url']) % 997))

    payload = {
        'updated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'count':   len(deduped),
        'stores':  len([s for s, n in per_store.items() if n]),
        'items':   deduped,
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))

    cats = {}
    for it in deduped:
        cats[it['cat']] = cats.get(it['cat'], 0) + 1
    print("\n" + "=" * 46)
    print(f"TOTAL {len(deduped)} items · {payload['stores']} stores · "
          f"{len({i['brand'] for i in deduped})} brands")
    print(f"NZ-designed: {sum(1 for i in deduped if i['nz'])}")
    print("By category:", dict(sorted(cats.items(), key=lambda kv: -kv[1])))
    if failed:
        print("No data from:", ', '.join(failed))
    print("=" * 46)

    if guard and len(deduped) < 100:             # guard: never publish a broken catalogue
        print("ERROR: suspiciously few items — not publishing.")
        sys.exit(1)
    return deduped


def merge(folder: str):
    """Combine part files written by --slice runs into the final products.json."""
    import glob, os
    items, per_store = [], {}
    for f in sorted(glob.glob(os.path.join(folder, '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        got = d['items'] if isinstance(d, dict) else d
        items.extend(got)
        for it in got:
            per_store[it['store']] = per_store.get(it['store'], 0) + 1
    write_payload(items, per_store, [], 'products.json')


if __name__ == '__main__':
    main()
