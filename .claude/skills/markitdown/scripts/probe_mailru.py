#!/usr/bin/env python3
"""TEMPORARY debug probe for Mail.ru Cloud stock links. Removed after use."""
import http.cookiejar
import json
import re
import sys
import urllib.request

url = sys.argv[1]
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [("User-Agent",
                  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")]

page = op.open(url, timeout=60).read().decode("utf-8", "replace")
print("PAGE LEN:", len(page))

for key in ["weblink_get", "stock_get", "\"stock\"", "tokens", "dispatcher",
            "csrf", "cloudSettings", "__PRELOADED", "serverSideProps"]:
    m = re.search(re.escape(key), page)
    if m:
        s = max(0, m.start() - 60)
        print(f"--- {key}: ...{page[s:m.start() + 300]}...".replace("\n", " ")[:400])

for host in sorted(set(re.findall(
        r'https?://[a-z0-9.-]*(?:cldmail|datacloudmail|cloclo)[a-z0-9.-]*\.ru[^"\'\\\s]*',
        page)))[:10]:
    print("DL-HOST:", host[:220])

for m in list(re.finditer(r"<script[^>]*>(.{0,20000}?)</script>", page, re.S))[:40]:
    body = m.group(1).strip()
    if ("stock" in body or "weblink" in body) and len(body) > 50:
        print("SCRIPT:", body[:1000].replace("\n", " "))
        print("======")

try:
    d = json.loads(op.open("https://cloud.mail.ru/api/v2/dispatcher?api=2",
                           timeout=60).read().decode("utf-8"))
    print("DISPATCHER BODY KEYS:", sorted(d.get("body", {}).keys()))
    print(json.dumps(d.get("body", {}), ensure_ascii=False)[:2000])
except Exception as e:  # noqa: BLE001
    print("dispatcher error:", e)

pid = url.split("/stock/")[-1].split("/public/")[-1].strip("/")
for cand in [
    f"https://cloud.mail.ru/api/v2/stock?ids={pid}&api=2",
    f"https://cloud.mail.ru/api/v2/stock/lite?ids={pid}&api=2",
    f"https://cloud.mail.ru/api/v2/stock/file?id={pid}&api=2",
    f"https://cloud.mail.ru/api/v2/folder?weblink={pid}&api=2",
]:
    try:
        r = op.open(cand, timeout=30)
        print("API OK:", cand, "->", r.read(500).decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001
        print("API ERR:", cand, "->", e)
