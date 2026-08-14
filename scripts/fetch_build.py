import json, time, sys, urllib.request

LONG = [
    ("BE", "Bloom Energy", 878.708),
    ("SNDK", "SanDisk", 724.363),
    ("CRWV", "CoreWeave", 556.073),
    ("IREN", "IREN", 401.036),
    ("CORZ", "Core Scientific", 389.087),
    ("APLD", "Applied Digital", 319.978),
    ("RIOT", "Riot Platforms", 142.166),
    ("CLSK", "CleanSpark", 104.470),
    ("SEI", "Solaris Energy Infra", 62.475),
    ("TE", "T1 Energy", 43.900),
]
SHORT = [
    ("NVDA", "Nvidia", 1568.257),
    ("ORCL", "Oracle", 1072.873),
    ("AVGO", "Broadcom", 1006.248),
    ("AMD", "AMD", 969.161),
    ("MU", "Micron", 583.686),
    ("TSM", "TSMC", 535.110),
    ("ASML", "ASML", 494.123),
    ("INTC", "Intel", 159.106),
]
HEADERS = {"User-Agent": "Mozilla/5.0"}


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


def build_group(items, prices):
    total = sum(v for _, _, v in items)
    out = []
    for tk, name, val in items:
        if tk not in prices:
            continue
        out.append({"t": tk, "n": name, "v": round(val, 1), "w": round(val / total * 100, 2)})
    return out, round(total, 1)


def main():
    prices = {}
    for tk, name, val in LONG + SHORT:
        try:
            prices[tk] = fetch(tk)
            print(f"{tk}: {len(prices[tk])} pts, last={prices[tk][-1]}", file=sys.stderr)
        except Exception as e:
            print(f"{tk}: FAILED {e}", file=sys.stderr)
        time.sleep(0.3)

    if len(prices) < 0.9 * len(LONG + SHORT):
        print("Too many ticker fetches failed — aborting, NOT writing data.", file=sys.stderr)
        sys.exit(1)

    long_group, long_total = build_group(LONG, prices)
    short_group, short_total = build_group(SHORT, prices)

    data = {
        "long": long_group,
        "short": short_group,
        "longTotalM": long_total,
        "shortTotalM": short_total,
        "prices": prices,
    }
    with open("data/dashboard_data.json", "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print("wrote data/dashboard_data.json", file=sys.stderr)


if __name__ == "__main__":
    main()
