#!/usr/bin/env python3
"""Build the Under Our Boots public dataset site from data/installations.csv.

Outputs (GitHub Pages, served from docs/):
  docs/index.html        Leaflet map (installation locations only) + searchable table
  docs/entry/<id>.html   one page per installation — the "Full entry on the website" target

Rules baked in: coordinates are installation/locality level only (the dataset
carries no site-level positions and none may be added); no archaeological site
or burial locations are ever shown. Rerun after any dataset update:
  python3 tools/build_site.py
"""
import csv, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "installations.csv")
DOCS = os.path.join(ROOT, "docs")

EPISODES = {  # dataset id -> (episode label, note)
    "102": ("Episode 1", "Fort Sill — published"),
    "186": ("Episode 2", "Kahoʻolawe — published"),
    "24": ("Episode 3", "NAS Fallon — published"),
    "26": ("Episode 4", "Fort Huachuca — in production"),
}

EV_COLORS = {"Confirmed": "#d94f30", "Probable": "#e8a13a",
             "Unverified": "#7a8794", "Refuted": "#5b8dd9"}

CSS = """
body{font-family:Georgia,'Times New Roman',serif;background:#14100c;color:#e8e0d0;margin:0;padding:0}
.wrap{max-width:860px;margin:0 auto;padding:24px 18px 60px}
a{color:#e8a13a} h1{font-size:1.7em;line-height:1.25;margin:.4em 0}
h2{font-size:1.05em;text-transform:uppercase;letter-spacing:.08em;color:#b8a888;margin:1.4em 0 .3em}
.meta{color:#b8a888;font-size:.95em} .badge{display:inline-block;padding:2px 10px;border-radius:10px;
background:#2a2118;border:1px solid #4a3b28;font-size:.85em;margin-right:6px}
.ep{border-color:#d94f30;color:#ffb59f} p{line-height:1.55}
.foot{margin-top:3em;border-top:1px solid #3a2f22;padding-top:1em;color:#8a7c64;font-size:.85em;line-height:1.5}
.src{word-break:break-word;font-size:.92em;line-height:1.6}
"""

def esc(s):
    return html.escape(s or "", quote=True)

def linkify(sources):
    parts = re.split(r"[;|]", sources or "")
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p.startswith("http://") or p.startswith("https://"):
            out.append(f'<a href="{esc(p)}" rel="noopener">{esc(p)}</a>')
        else:
            out.append(esc(p))
    return "<br>".join(out)

def entry_page(r):
    eid = r["id"]
    ep = EPISODES.get(eid)
    ep_html = f'<span class="badge ep">{esc(ep[0])} — {esc(ep[1])}</span>' if ep else ""
    founded = r["founded_year"] or "—"
    years = f' ({esc(r["years"])})' if r["years"] else ""
    flags = esc(r["flags"]) if r["flags"] else "None documented"
    flag_detail = f'<p>{esc(r["flag_detail"])}</p>' if r["flag_detail"] else ""
    rel_note = f'<p>{esc(r["relationship_note"])}</p>' if r["relationship_note"] else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(r['name'])} — Under Our Boots</title><style>{CSS}</style></head>
<body><div class="wrap">
<p class="meta"><a href="../index.html">← All 404 installations</a></p>
<h1>{esc(r['name'])}</h1>
<p class="meta">{esc(r['location'])} · {esc(r['region'])} · {esc(r['builder'])} · founded {esc(founded)}{years}</p>
<p>{ep_html}<span class="badge">Evidence: {esc(r['evidence'])}</span>
<span class="badge">{esc(r['relationship'])}</span></p>
<h2>What lies beneath</h2><p>{esc(r['beneath'])}</p>
<h2>Relationship</h2><p>{esc(r['relationship'])}</p>{rel_note}
<h2>Flags</h2><p>{flags}</p>{flag_detail}
<h2>Sources</h2><p class="src">{linkify(r['sources'])}</p>
<div class="foot">Under Our Boots — the history buried beneath America's military bases.
Researched by Claude, verified by Muse. This page shows the installation's public
location only; archaeological site and burial locations are never published.</div>
</div></body></html>"""

def main():
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    os.makedirs(os.path.join(DOCS, "entry"), exist_ok=True)
    points = []
    for r in rows:
        with open(os.path.join(DOCS, "entry", f"{r['id']}.html"), "w", encoding="utf-8") as f:
            f.write(entry_page(r))
        points.append({"id": r["id"], "name": r["name"], "loc": r["location"],
                       "lat": float(r["latitude"]), "lng": float(r["longitude"]),
                       "ev": r["evidence"], "rel": r["relationship"]})
    geo = {"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "geometry": {"type": "Point", "coordinates": [p["lng"], p["lat"]]},
         "properties": {"id": p["id"], "name": p["name"], "evidence": p["ev"],
                        "relationship": p["rel"]}} for p in points]}
    with open(os.path.join(ROOT, "data", "installations.geojson"), "w", encoding="utf-8") as f:
        json.dump(geo, f, ensure_ascii=False, indent=1)
    table_rows = "\n".join(
        f'<tr><td><a href="entry/{p["id"]}.html">{esc(p["name"])}</a></td>'
        f'<td>{esc(p["loc"])}</td><td>{esc(p["ev"])}</td><td>{esc(p["rel"])}</td></tr>'
        for p in points)
    index = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Under Our Boots — 404 installations</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>{CSS}#map{{height:62vh;border:1px solid #4a3b28}}
table{{border-collapse:collapse;width:100%;font-size:.92em}}
td,th{{border-bottom:1px solid #3a2f22;padding:6px 8px;text-align:left;vertical-align:top}}
input{{width:100%;padding:9px;background:#241b12;color:#e8e0d0;border:1px solid #4a3b28;font-size:1em}}
</style></head>
<body><div class="wrap">
<h1>Under Our Boots</h1>
<p class="meta">404 military installations built on Indigenous and significant sites —
the dataset behind the series. Researched by Claude, verified by Muse.</p>
<div id="map"></div>
<p class="meta">Map shows installation locations only — never archaeological sites or burials.
Colours: <span style="color:#d94f30">Confirmed</span> · <span style="color:#e8a13a">Probable</span> ·
<span style="color:#7a8794">Unverified</span> · <span style="color:#5b8dd9">Refuted</span></p>
<input id="q" type="search" placeholder="Search installations, places, nations…">
<table><thead><tr><th>Installation</th><th>Location</th><th>Evidence</th><th>Relationship</th></tr></thead>
<tbody id="rows">{table_rows}</tbody></table>
<div class="foot">Under Our Boots — a TikTok and YouTube Shorts series by Shefton Berthold.
Dataset: see the GitHub repository (data/installations.csv). Facts are stated at their
evidence level; report an error via the repository's Issues.</div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
var pts = {json.dumps(points, ensure_ascii=False)};
var colors = {json.dumps(EV_COLORS)};
var map = L.map('map').setView([30, -40], 2);
L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
  {{attribution: '&copy; OpenStreetMap contributors'}}).addTo(map);
pts.forEach(function(p){{
  L.circleMarker([p.lat, p.lng], {{radius:5, color:colors[p.ev] || '#999', weight:2}})
    .bindPopup('<a href="entry/' + p.id + '.html">' + p.name + '</a><br>' + p.loc + '<br>' + p.ev)
    .addTo(map);
}});
document.getElementById('q').addEventListener('input', function(){{
  var q = this.value.toLowerCase();
  document.querySelectorAll('#rows tr').forEach(function(tr){{
    tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}});
</script></body></html>"""
    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
        f.write(index)
    print(f"built {len(rows)} entry pages + index + geojson")

if __name__ == "__main__":
    sys.exit(main())
