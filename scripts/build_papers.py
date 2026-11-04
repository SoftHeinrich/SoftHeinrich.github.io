#!/usr/bin/env python3
"""Regenerate the <main> of papers.html from ORCID works + data/papers_extra.json.
ORCID is the source; extras are manual entries (works missing from ORCID) merged by DOI.
Venues come from Crossref unless overridden. Rankings are only what data/papers_extra.json lists.
Run from anywhere:  python3 scripts/build_papers.py
"""
import json, re, html, pathlib, urllib.request
ROOT = pathlib.Path(__file__).resolve().parent.parent
cfg = json.load(open(ROOT / "data/papers_extra.json"))
e = html.escape

def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "personal-site-build"})
    return json.load(urllib.request.urlopen(req, timeout=30))

def crossref_venue(doi):
    m = get("https://api.crossref.org/works/" + doi)["message"]
    return (m.get("event") or {}).get("name") or (m.get("container-title") or [None])[0]

TYPES = {"conference-paper": "Conference paper", "journal-article": "Journal article"}
papers = {}
base = f"https://pub.orcid.org/v3.0/{cfg['orcid']}"
for g in get(base + "/works")["group"]:
    s = g["work-summary"][0]
    w = get(f"{base}/work/{s['put-code']}")
    doi = next((x["external-id-value"] for x in w["external-ids"]["external-id"] if x["external-id-type"] == "doi"), None)
    if not doi or doi in cfg["exclude_dois"] or w["type"].lower() not in TYPES:
        continue
    d = w["publication-date"]; n = lambda k: int((d.get(k) or {}).get("value") or 0)
    venue = cfg["venue_overrides"].get(doi) or (w.get("journal-title") or {}).get("value") or crossref_venue(doi)
    papers[doi.lower()] = dict(doi=doi, title=w["title"]["title"]["value"], venue=venue,
        authors=[c["credit-name"]["value"] for c in w["contributors"]["contributor"]],
        date=(n("year"), n("month"), n("day")))
for x in cfg["extras"]:  # ORCID wins if it later gains the same DOI
    papers.setdefault(x["doi"].lower(), dict(doi=x["doi"], title=x["title"], venue=x["venue"],
        authors=x["authors"], date=(x["year"], x.get("month", 0), x.get("day", 0))))

out = ['<h1>Papers</h1>',
 f'<p class="meta">Source: <a href="https://orcid.org/{cfg["orcid"]}">ORCID</a> plus manually added entries; venues from Crossref; conference rankings from the <a href="https://portal.core.edu.au/conf-ranks/">CORE portal</a> (ICORE2026). CCF (2022 list) ranks are as cross-checked on third-party copies of the list. Rankings are shown only where confirmed.</p>']
year = None; items = []
def flush():
    if items: out.append('<ul class="items">\n' + "\n".join(items) + '\n</ul>')
for p in sorted(papers.values(), key=lambda p: p["date"], reverse=True):
    if p["date"][0] != year:
        flush(); items = []; year = p["date"][0]; out.append(f"<h2>{year}</h2>")
    a = ", ".join(f'<strong><u>{e(x)}</u></strong>' if x == cfg["me"] else e(x) for x in p["authors"])
    r = cfg["rankings"].get(p["doi"], {})
    rk = "".join(f" · {k} {r[k2]}" for k, k2 in (("CCF", "ccf"), ("CORE", "core")) if k2 in r)
    items.append(f'<li><strong>{e(p["title"])}</strong><br><span class="meta">{a}</span><br>'
                 f'<span class="meta">{e(p["venue"])}{rk} · <a href="https://doi.org/{p["doi"]}">DOI {p["doi"]}</a></span></li>')
flush()
f = ROOT / "papers.html"
f.write_text(re.sub(r"<main>.*?</main>", lambda _: "<main>\n" + "\n".join(out) + "\n</main>", f.read_text(), flags=re.S))
print(f"wrote {len(papers)} papers")
