import json, time, sys, urllib.request

# Holdings come from data/holdings_13f.json (SEC 13F information tables).
# The last filing in that file is the "latest" basket, the one before it the "prev" basket.
# Each quarter: append the new filing there; nothing in this script needs to change.
HOLDINGS_FILE = "data/holdings_13f.json"
OUT_FILE = "data/dashboard_data.json"
BASKET_COVERAGE = 0.95  # take the largest common-stock positions until they cover 95% of long equity value
HEADERS = {"User-Agent": "Mozilla/5.0"}
CAT_ORDER = {"신규": 0, "확대": 1, "축소": 2, "유지": 3, "청산": 4}
TYPE_LABEL = {"": "주식", "Call": "콜", "Put": "풋"}


def fetch(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    result = data["chart"]["result"][0]
    ts = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    out = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        d = time.strftime("%Y-%m-%d", time.gmtime(t))
        out.append([d, round(c, 4)])
    return out


def aggregate(rows):
    """Sum value/shares per (ticker, put/call)."""
    agg = {}
    for r in rows:
        key = (r["t"], r["pc"])
        a = agg.setdefault(key, {"t": r["t"], "n": r["n"], "pc": r["pc"], "v": 0, "sh": 0})
        a["v"] += r["v"]
        a["sh"] += r["sh"]
    return agg


def basket(filing):
    commons = sorted((a for a in aggregate(filing["rows"]).values() if a["pc"] == ""), key=lambda a: -a["v"])
    equity_total = sum(a["v"] for a in commons)
    picked, acc = [], 0
    for a in commons:
        if acc >= BASKET_COVERAGE * equity_total:
            break
        picked.append(a)
        acc += a["v"]
    return picked, equity_total


def weigh(picked, prices):
    kept = [a for a in picked if a["t"] in prices]
    total = sum(a["v"] for a in kept)
    group = [{"t": a["t"], "n": a["n"], "v": round(a["v"] / 1e6, 1), "w": round(a["v"] / total * 100, 2)} for a in kept]
    return group, total


def changes(prev, latest):
    p, l = aggregate(prev["rows"]), aggregate(latest["rows"])
    out = []
    for key in set(p) | set(l):
        a, b = p.get(key), l.get(key)
        s1, s2 = (a["sh"] if a else 0), (b["sh"] if b else 0)
        if s1 == 0:
            cat = "신규"
        elif s2 == 0:
            cat = "청산"
        elif s2 > s1:
            cat = "확대"
        elif s2 < s1:
            cat = "축소"
        else:
            cat = "유지"
        ref = b or a
        out.append({
            "t": ref["t"], "n": ref["n"], "type": TYPE_LABEL[ref["pc"]], "cat": cat,
            "s1": s1, "s2": s2,
            "v1": round((a["v"] if a else 0) / 1e6, 1), "v2": round((b["v"] if b else 0) / 1e6, 1),
        })
    out.sort(key=lambda c: (CAT_ORDER[c["cat"]], -max(c["v1"], c["v2"])))
    return out


def option_total(filing, pc):
    return round(sum(r["v"] for r in filing["rows"] if r["pc"] == pc) / 1e6, 1)


def main():
    holdings = json.load(open(HOLDINGS_FILE, encoding="utf-8"))
    prev_f, latest_f = holdings["filings"][-2], holdings["filings"][-1]
    latest_pick, latest_eq = basket(latest_f)
    prev_pick, prev_eq = basket(prev_f)

    tickers = []
    for a in latest_pick + prev_pick:
        if a["t"] not in tickers:
            tickers.append(a["t"])

    prices = {}
    for tk in tickers:
        try:
            prices[tk] = fetch(tk)
            print(f"{tk}: {len(prices[tk])} pts, last={prices[tk][-1]}", file=sys.stderr)
        except Exception as e:
            print(f"{tk}: FAILED {e}", file=sys.stderr)
        time.sleep(0.3)

    if len(prices) < 0.9 * len(tickers):
        print("Too many ticker fetches failed — aborting, NOT writing data.", file=sys.stderr)
        sys.exit(1)

    long_group, long_total = weigh(latest_pick, prices)
    prev_group, prev_total = weigh(prev_pick, prices)

    data = {
        "filing": {
            "period": latest_f["period"], "filed": latest_f["filed"], "accession": latest_f["accession"],
            "prevPeriod": prev_f["period"], "prevFiled": prev_f["filed"],
            "totalM": round(sum(r["v"] for r in latest_f["rows"]) / 1e6, 1),
            "positions": len(latest_f["rows"]),
            "putM": option_total(latest_f, "Put"), "prevPutM": option_total(prev_f, "Put"),
            "callM": option_total(latest_f, "Call"), "prevCallM": option_total(prev_f, "Call"),
        },
        "long": long_group,
        "longTotalM": round(long_total / 1e6, 1),
        "longCovPct": round(long_total / latest_eq * 100, 1),
        "prev": prev_group,
        "prevTotalM": round(prev_total / 1e6, 1),
        "prevCovPct": round(prev_total / prev_eq * 100, 1),
        "changes": changes(prev_f, latest_f),
        "prices": prices,
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    print(f"wrote {OUT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
