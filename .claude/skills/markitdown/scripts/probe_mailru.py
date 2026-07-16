#!/usr/bin/env python3
"""TEMPORARY debug probe for Mail.ru Cloud stock links. Removed after use."""
import http.cookiejar
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import _extract_json_object, _ep_url, UA  # noqa: E402

url = sys.argv[1]
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [("User-Agent", UA)]

page = op.open(url, timeout=60).read().decode("utf-8", "replace")
print("PAGE LEN:", len(page))

disp = _extract_json_object(page, "dispatcher") or {}
print("DISPATCHER:", json.dumps(disp, ensure_ascii=False)[:1200])

ssf = _extract_json_object(page, "serverSideFolders") or {}
print("SERVERSIDEFOLDERS FULL:", json.dumps(ssf, ensure_ascii=False)[:5000])

folder = ssf.get("folder") or {}
items = folder.get("list") or []
bundle = folder.get("bundle") or ""
stock_url = _ep_url(disp, "stock") or ""
weblink_get = _ep_url(disp, "weblink_get") or ""
get_url = _ep_url(disp, "get") or ""

for it in items:
    name = str(it.get("name", ""))
    sid = str(it.get("stock", ""))
    token = str(it.get("dwl_token", ""))
    qname = urllib.parse.quote(name)
    qsid = urllib.parse.quote(sid, safe="/")
    qtok = urllib.parse.quote(token, safe="")
    cands = []
    for base in [stock_url, get_url, weblink_get]:
        if not base:
            continue
        b = base.rstrip("/")
        if token:
            cands += [f"{b}/{qtok}", f"{b}/{qtok}/{qname}",
                      f"{b}/{qsid}?key={qtok}", f"{b}/{qsid}?token={qtok}",
                      f"{b}/{qsid}?dwl_token={qtok}"]
        cands += [f"{b}/{qsid}"]
    for c in dict.fromkeys(cands):
        try:
            r = op.open(c, timeout=30)
            head = r.read(80)
            print("TRY OK ", r.status, r.headers.get("Content-Type"),
                  r.headers.get("Content-Length"), c[:180], "HEAD:", head[:40])
            break
        except Exception as e:  # noqa: BLE001
            print("TRY ERR", getattr(e, 'code', '?'), c[:180], "->", e)
