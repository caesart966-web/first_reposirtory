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
HDRS = {"User-Agent": UA, "Referer": "https://cloud.mail.ru/",
        "Origin": "https://cloud.mail.ru"}


def GET(u, data=None, extra=None):
    h = dict(HDRS)
    if extra:
        h.update(extra)
    req = urllib.request.Request(u, headers=h, data=data)
    return op.open(req, timeout=45)


page = GET(url).read().decode("utf-8", "replace")
disp = _extract_json_object(page, "dispatcher") or {}
ssf = _extract_json_object(page, "serverSideFolders") or {}
folder = ssf.get("folder") or {}
it = (folder.get("list") or [{}])[0]
name, sid, tok = it.get("name", ""), it.get("stock", ""), it.get("dwl_token", "")
stock_url = (_ep_url(disp, "stock") or "").rstrip("/")
print("stock_url:", stock_url, "| sid:", sid[:60], "| tok:", tok[:40], "...")

qname = urllib.parse.quote(str(name))
qsid = urllib.parse.quote(str(sid), safe="/")
qtok = urllib.parse.quote(str(tok), safe="")

cands = [
    f"{stock_url}/{qsid}?key={qtok}",
    f"{stock_url}/get/{qtok}",
    f"{stock_url}/get/{qtok}/{qname}",
    f"{stock_url}/{qtok}",
    f"{stock_url}/{qtok}/{qname}",
    f"{stock_url}/{qsid}",
]
for c in cands:
    try:
        r = GET(c)
        head = r.read(64)
        print("WITH-REFERER OK", r.status, r.headers.get("Content-Type"),
              r.headers.get("Content-Length"), c[:170], head[:32])
        break
    except Exception as e:  # noqa: BLE001
        print("WITH-REFERER ERR", getattr(e, "code", "?"), c[:170])

# CSRF flow
csrf = None
for how, u, data in [
    ("POST", "https://cloud.mail.ru/api/v2/tokens/csrf",
     b"api=2&email=anonym&x-email=anonym"),
    ("GET", "https://cloud.mail.ru/api/v2/tokens/csrf?api=2", None),
]:
    try:
        r = GET(u, data=data,
                extra={"Content-Type": "application/x-www-form-urlencoded"}
                if data else None)
        body = json.loads(r.read().decode("utf-8"))
        csrf = (body.get("body") or {}).get("token")
        print("CSRF", how, "->", csrf)
        if csrf:
            break
    except Exception as e:  # noqa: BLE001
        print("CSRF", how, "ERR:", e)

pid = url.split("/stock/")[-1].strip("/")
if csrf:
    for c in [
        f"https://cloud.mail.ru/api/v2/stock?ids={pid}&api=2&token={csrf}",
        f"https://cloud.mail.ru/api/v2/stock/download?ids={pid}&api=2&token={csrf}",
        f"https://cloud.mail.ru/api/v2/zip?weblink_list=[]&stock_list=%5B%22{pid}%22%5D&api=2&token={csrf}",
    ]:
        try:
            r = GET(c)
            print("API OK:", c[:120], "->", r.read(600).decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            body = ""
            if hasattr(e, "read"):
                try:
                    body = e.read(300).decode("utf-8", "replace")
                except Exception:  # noqa: BLE001
                    pass
            print("API ERR:", getattr(e, "code", "?"), c[:120], "->", body)
