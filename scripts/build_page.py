"""Validate data/dashboard_data.json and inject it into template/dashboard.html -> dashboard_final.html."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "dashboard_data.json")
TEMPLATE = os.path.join(ROOT, "template", "dashboard.html")
OUT = os.path.join(ROOT, "dashboard_final.html") if len(sys.argv) < 2 else sys.argv[1]

raw = open(DATA, encoding="utf-8").read()
d = json.loads(raw)
for key in ("filing", "long", "prev", "changes", "prices"):
    assert key in d, f"missing key: {key}"
assert len(d["long"]) >= 8 and len(d["prev"]) >= 8, "basket too small"
for h in d["long"] + d["prev"]:
    assert h["t"] in d["prices"], f"no prices for {h['t']}"
for tk, series in d["prices"].items():
    assert len(series) >= 100, f"{tk} has too few price points: {len(series)}"

tpl = open(TEMPLATE, encoding="utf-8").read()
assert tpl.count("__DATA_JSON__") == 1, "template placeholder missing"
html = tpl.replace("__DATA_JSON__", raw.replace("</", "<\/"))
open(OUT, "w", encoding="utf-8").write(html)
latest = max(s[-1][0] for s in d["prices"].values())
print(f"OK {len(d['prices'])} tickers, 13F {d['filing']['period']}, latest price date {latest} -> {OUT}")
