#!/usr/bin/env python3
"""
Lucknow Deal Command Center - free auto-updater (multi-city, deals + tenants).
Runs every few hours via GitHub Actions. Standard library only, no API keys.

Writes two files the app reads automatically:
  data.json  -> DEALS + market signals: auctions, RERA-stalled, listings, demand (Dashboard + Deals + Map)
  leads.json -> TENANT LEADS: brand, category, size, locality, why-now, source + a LinkedIn route

Every record is tagged with "city" so the app's city switch can filter it.

HOW TO ADD A CITY: add its name to CITIES and (optionally) its corridors to CORRIDORS_BY_CITY.
Contact-finding stays legitimate: public LinkedIn / enquiry routes only, never scraped private data.
"""
import json, re, urllib.request, urllib.parse, xml.etree.ElementTree as ET

# ============ CITIES (add more here; Lucknow is default) ============
CITIES = ["Lucknow"]        # e.g. ["Lucknow", "Kanpur", "Noida", "Gurugram"]

CORRIDORS_BY_CITY = {
 "Lucknow": ["Gomti Nagar","Vibhuti Khand","Hazratganj","Shaheed Path","Faizabad Road","Kanpur Road",
   "Sultanpur Road","Alambagh","Chinhat","Aliganj","Indira Nagar","Amausi","Transport Nagar","Sushant Golf City"],
}

# ============ Seed data (present before the first run) ============
SEED = [
 {"title":"Showroom, sector 4 — bank auction","type":"Auction","city":"Lucknow","corridor":"Gomti Nagar","price":24000000,"rent":170000,"area":3200,"distress":5,"fit":5,"margin":4,"timing":4,"reason":"SARFAESI e-auction, reserve below circle rate","source":"IBAPI","date":"2026-08-05","phone":"919000000001","lat":26.855,"lng":81.010},
 {"title":"Office block — stalled 3 yrs","type":"Stalled","city":"Lucknow","corridor":"Shaheed Path","price":41000000,"rent":300000,"area":6000,"distress":5,"fit":5,"margin":5,"timing":3,"reason":"On RERA abeyance list, promoter keen to exit","source":"UP-RERA","date":"2026-08-03","phone":"919000000002","lat":26.800,"lng":81.020},
 {"title":"Retail unit — DRT auction","type":"Auction","city":"Lucknow","corridor":"Hazratganj","price":32000000,"rent":260000,"area":2600,"distress":5,"fit":4,"margin":4,"timing":3,"reason":"DRT notice, prime high-street frontage","source":"bankeauctions","date":"2026-08-02","phone":"919000000005","lat":26.850,"lng":80.945},
 {"title":"Warehouse — UPSIDA plot","type":"Plot","city":"Lucknow","corridor":"Transport Nagar","price":18000000,"rent":150000,"area":12000,"distress":2,"fit":4,"margin":5,"timing":4,"reason":"UPSIDA e-auction; logistics demand rising","source":"UPSIDA","date":"2026-08-01","phone":"919000000006","lat":26.800,"lng":80.870},
 {"title":"Showroom shell — overdue project","type":"Stalled","city":"Lucknow","corridor":"Sultanpur Road","price":22000000,"rent":160000,"area":3000,"distress":4,"fit":4,"margin":4,"timing":4,"reason":"Completion date passed, 0% QPR progress","source":"UP-RERA","date":"2026-07-30","phone":"919000000007","lat":26.780,"lng":81.060},
 {"title":"Bank-owned commercial unit","type":"Auction","city":"Lucknow","corridor":"Alambagh","price":15000000,"rent":120000,"area":2000,"distress":5,"fit":3,"margin":4,"timing":3,"reason":"BAANKNET NPA listing, quick sale","source":"BAANKNET","date":"2026-07-28","phone":"919000000011","lat":26.815,"lng":80.905}
]
SEED_LEADS = [
 {"name":"Croma","category":"Electronics","city":"Lucknow","space":"","locality":"Gomti Nagar","signal":"Croma expanding across UP — Lucknow store likely","source":"example","link":"","date":"","linkedin":"https://www.linkedin.com/search/results/people/?keywords=Croma%20retail%20expansion","stage":"Detected"},
 {"name":"UNIQLO","category":"Fashion / Footwear","city":"Lucknow","space":"","locality":"Lucknow","signal":"UNIQLO entering Lucknow — large-format EBO","source":"example","link":"","date":"","linkedin":"https://www.linkedin.com/search/results/people/?keywords=UNIQLO%20India%20real%20estate","stage":"Detected"},
 {"name":"Haldiram's QSR","category":"QSR / F&B","city":"Lucknow","space":"","locality":"Faizabad Road","signal":"Haldiram's named Lucknow a key QSR expansion city","source":"example","link":"","date":"","linkedin":"https://www.linkedin.com/search/results/people/?keywords=Haldiram%20expansion","stage":"Detected"},
 {"name":"Delhivery","category":"Warehouse / Logistics","city":"Lucknow","space":"20000 sqft","locality":"Transport Nagar","signal":"3PL warehousing demand rising in the logistics belt","source":"example","link":"","date":"","linkedin":"https://www.linkedin.com/search/results/people/?keywords=Delhivery%20network%20expansion","stage":"Detected"}
]

# ============ Query sets ============
# Deal queries: (type, template). {city} is substituted.
DEAL_QUERIES = [
 ("Auction", 'bank auction commercial property {city}'),
 ("Auction", 'SARFAESI e-auction property {city}'),
 ("Auction", 'NPA property auction {city}'),
 ("Stalled", '{city} stalled project RERA'),
 ("Stalled", 'RERA {city} project abeyance OR stalled'),
 ("Listing", 'commercial property for sale {city}'),
 ("Listing", 'showroom OR office for sale {city}'),
 ("Demand", 'new store {city}'),
 ("Demand", '{city} retail expansion'),
 ("Demand", 'warehouse lease requirement {city}'),
]
LEAD_QUERIES = [
 '"opens in {city}"', 'new store {city}', 'new showroom {city}', '{city} retail expansion',
 'franchise {city}', '{city} office space lease', 'hiring {city} expansion',
 '{city} "store manager" hiring', 'brand "to open" {city}', 'funding brand offline stores {city}',
]
SCORES = {  # distress, fit, margin, timing
 "Auction":(5,3,4,4), "Stalled":(4,4,4,4), "Listing":(2,4,4,3), "Demand":(1,4,3,5), "Plot":(2,4,5,4)
}
CATEGORY_KEYWORDS = {
 "Jewellery":["jewel","tanishq","kalyan","indriya","malabar","senco","joyalukkas"],
 "QSR / F&B":["cafe","coffee","restaurant","qsr","burger","pizza","biryani","haldiram","kfc","domino"],
 "Fashion / Footwear":["fashion","apparel","footwear","uniqlo","zudio","shoe","clothing","souled","trends"],
 "Electronics":["electronic","croma","reliance digital","mobile","vijay sales","cashify","appliance"],
 "Grocery / Retail":["dmart","supermarket","grocery","mega mart","hypermarket","retail chain"],
 "Quick-commerce":["blinkit","zepto","instamart","dark store","quick commerce","quick-commerce"],
 "Pharmacy / Health":["pharmacy","clinic","hospital","diagnostic","apollo","medplus","dental","eye"],
 "Education":["coaching","academy","school","edtech","institute","aakash","allen","physics wallah","preschool"],
 "Co-working / Office":["coworking","co-working","office","workspace","awfis","smartworks","it park","bpo","gcc"],
 "Fitness / Salon":["gym","fitness","salon","spa","cult","anytime","looks salon","wellness"],
 "Auto / EV":["ev ","electric vehicle","dealership","royal enfield","byd","automobile","two-wheeler","cars24","spinny"],
 "Banking / NBFC":["bank","nbfc","finance","insurance","branch","muthoot","bajaj finance"],
 "Warehouse / Logistics":["warehouse","logistics","3pl","fulfilment","fulfillment","delhivery","ecom express"],
 "Hospitality":["hotel","hospitality","resort","serviced apartment","banquet","oyo","treebo"],
}

def fetch_rss(q):
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:60d") + "&hl=en-IN&gl=IN&ceid=IN:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; DealRadar/1.0)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()

def items_of(xml_bytes, city):
    out = []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return out
    corrs = CORRIDORS_BY_CITY.get(city, [])
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        if not title:
            continue
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        s_el = it.find("source")
        src = (s_el.text if (s_el is not None and s_el.text) else "News").strip()
        corr = next((c for c in corrs if c.lower() in title.lower()), city)
        out.append({"title": title[:130], "link": link, "date": pub[:16], "source": src, "corridor": corr})
    return out

def category_of(t):
    tl = t.lower()
    for cat, ks in CATEGORY_KEYWORDS.items():
        if any(k in tl for k in ks):
            return cat
    return "General retail / office"

def size_of(t):
    m = re.search(r'([\d,]{3,7})\s*(sq\.?\s?ft|sqft|square feet)', t, re.I)
    return (m.group(1).replace(",", "") + " sqft") if m else ""

def brand_of(title):
    t = re.split(r'\bto open\b|\bopens\b|\bplans\b|\bexpands\b|\bexpansion\b|\bin \w+\b|\bstores\b|:|\||–|—| - ', title)[0].strip()
    return (t[:60] or title[:60]).strip()

def build_deals():
    out = list(SEED)
    seen = set(r["title"].lower() for r in out)
    fetched = []
    for city in CITIES:
        for dtype, tpl in DEAL_QUERIES:
            q = tpl.format(city=city)
            try: items = items_of(fetch_rss(q), city)
            except Exception: items = []
            d, f, m, tm = SCORES.get(dtype, (2, 4, 3, 4))
            for it in items:
                k = it["title"].lower()
                if k in seen: continue
                seen.add(k)
                fetched.append({"title": it["title"], "type": dtype, "city": city, "corridor": it["corridor"],
                    "price": 0, "rent": 0, "area": 0, "distress": d, "fit": f, "margin": m, "timing": tm,
                    "reason": (dtype + " signal via " + it["source"])[:140], "source": "News: " + it["source"],
                    "date": it["date"], "phone": "", "lat": None, "lng": None, "link": it["link"]})
    out = list(SEED) + fetched[:120]
    for i, r in enumerate(out): r["id"] = "r" + str(i)
    return out

def build_leads():
    out = list(SEED_LEADS)
    seen = set(l["name"].lower() for l in out)
    for city in CITIES:
        for tpl in LEAD_QUERIES:
            q = tpl.format(city=city)
            try: items = items_of(fetch_rss(q), city)
            except Exception: items = []
            for it in items:
                brand = brand_of(it["title"])
                if not brand or brand.lower() in seen: continue
                seen.add(brand.lower())
                out.append({"name": brand, "category": category_of(it["title"]), "city": city, "person": "", "budget": "",
                    "space": size_of(it["title"]), "locality": it["corridor"], "signal": it["title"],
                    "source": it["source"], "link": it["link"], "date": it["date"],
                    "linkedin": "https://www.linkedin.com/search/results/people/?keywords=" + urllib.parse.quote(brand + " expansion real estate"),
                    "stage": "Detected"})
    return out[:100]

def main():
    data = build_deals()
    json.dump(data, open("data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    leads = build_leads()
    json.dump(leads, open("leads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("cities=%s | %d deal records | %d tenant leads" % (",".join(CITIES), len(data), len(leads)))

if __name__ == "__main__":
    main()
