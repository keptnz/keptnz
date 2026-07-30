# KEPT — Shop New Zealand stores

Swipe through fashion from New Zealand's best stores in one place.
Save what you love, skip what you don't — and never be shown it again.
Buying happens on the retailer's own site.

Live: https://keptnz.netlify.app

---

## What's in here

| File | What it does |
|---|---|
| `index.html` | The whole app (design, swiping, saving, matches, feedback, analytics) |
| `products.json` | The catalogue — refreshed automatically every day |
| `scripts/fetch_products.py` | **The data engine.** Pulls live products from 62 NZ stores |
| `.github/workflows/refresh-catalogue.yml` | Runs the engine daily on GitHub's servers, free |
| `manifest.webmanifest`, `sw.js`, `icon-*.png` | Makes it installable on a phone like a real app |
| `netlify.toml` | Tells Netlify never to serve a stale catalogue |

---

## How the catalogue keeps itself up to date

1. Every day at **6am NZ time**, GitHub runs `scripts/fetch_products.py`.
2. That script visits each store in its `STORES` list and reads their public
   product feed (`/products.json` — most NZ fashion retailers run on Shopify).
3. It cleans, categorises and de-duplicates everything, flags NZ-designed
   labels, and writes a fresh `products.json`.
4. If anything changed, it commits the new file. Netlify sees the commit and
   redeploys automatically.
5. Next time anyone opens the app, they get the new catalogue.

Nobody has to touch it. New arrivals appear, sold-out lines drop off.

**Safety net:** if a store is down or a feed breaks, that store is skipped and
the rest still publish. If the total ever comes back under 100 items the script
fails on purpose, so a broken run can never wipe your catalogue.

### Adding a new store

Open `scripts/fetch_products.py` and add one line to `STORES`:

```python
("storedomain.co.nz", "Store Name", 5),   # 5 = how many pages to read
```

Commit it. That's the whole job — if the store runs on Shopify, it just works.
To check first, open `https://storedomain.co.nz/products.json` in a browser:
if you see product data, it'll work.

### Running it yourself

```bash
python3 scripts/fetch_products.py
```

No installs needed — it only uses the Python standard library.

---

## Shop near you (location filter)

The pin icon in the header filters to brands that have a **physical store** in a
chosen city and suburb, so someone can find things they can go and try on.

Locations live in `index.html` in the `STORE_LOCATIONS` block:

```js
"Kowtow": [["Auckland","Newmarket"],["Wellington","Te Aro"]],
```

Add a retailer by adding a line. Currently verified from each brand's own
store-locator page: Deadly Ponies, Ruby, Juliette Hogan, Karen Walker, Kowtow,
Workshop and Mi Piaci. Everything else is treated as online-only until you add
its stores — worth expanding, and worth re-checking occasionally as shops move.

**Important:** this says *this brand has a shop near you*, not *this exact item
is on the shelf there*. Real per-store stock needs a data feed from the
retailer's own till system, which is a partnership conversation, not something
a public product feed can tell you. The wording in the app is honest about that.

---

## Analytics

Open `index.html` and find the `ANALYTICS` block near the top of the script:

```js
const ANALYTICS = { plausibleDomain: "", ga4: "", sendSessionSummary: true };
```

- Leave it as is and you still get a **session summary** in your Netlify
  **Forms → analytics** inbox: how long someone used it, how many pieces they
  saved and skipped, and the actual items they saved.
- Want charts? Put your domain in `plausibleDomain` (Plausible) or your
  measurement ID in `ga4` (Google Analytics) and events flow there too.

Tracked events: `app_open`, `save`, `skip`, `click_through`, `department`,
`coming_soon_interest`, `search`, `view_saved`, `view_matches`,
`feedback_sent`, `install_prompt_opened`.

`coming_soon_interest` is the useful one for deciding what to build next — it
tells you who's tapping Home, Beauty, Kids and Lifestyle.

---

## Feedback

Testers can leave a star rating and a comment from **Profile → Share feedback**.
It lands in your Netlify **Forms → feedback** inbox.

---

## Where saved items live

On each person's own phone (browser local storage), so their saves and skips
persist between visits. It doesn't follow them to another device — that needs
user accounts and a database, which is the next real build step.

---

## What's next

- **Accounts + database** (e.g. Supabase) so saves sync across devices and you
  can email someone when a saved piece goes on sale.
- **Affiliate links** — join Commission Factory / Rakuten / Awin, then wrap the
  outbound product links so every sale earns commission.
- **More departments** — Home, Beauty, Kids and Lifestyle are already in the
  navigation marked "soon".
