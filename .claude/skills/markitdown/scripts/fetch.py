#!/usr/bin/env python3
"""
fetch.py — download files from URLs listed in a links file (inbox/links.txt).

Lets users convert files that are too big for GitHub (web upload: 25 MB,
git push: 100 MB): they paste a share link instead, CI downloads the file to
a temp dir, the converter turns it into Markdown, and only the small .md is
committed — the original never enters git history.

Supported link types:
  * direct links   — anything curl-able over http(s)
  * Dropbox        — ?dl=0 is rewritten to ?dl=1 (direct download)
  * Google Drive   — share links; uses `gdown` when installed (handles the
                     large-file confirm page), otherwise a best-effort
                     uc?export=download request
  * Yandex Disk    — public links via cloud-api.yandex.net

Links file format: one URL per line; blank lines and lines starting with #
are ignored.

State: processed URLs are recorded in a JSON state file (default
converted/.links_done.json) and skipped on later runs, so editing the links
file never re-downloads what was already converted. Remove an entry from the
state file (or pass --refetch) to force a re-download.

Usage:
    python fetch.py inbox/links.txt --out /tmp/fetched \
        --state converted/.links_done.json
    python fetch.py --url https://example.com/report.pdf --out /tmp/fetched

Prints one downloaded file path per line. Missing/empty links file is not an
error (exit 0) so CI can run this unconditionally.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB safety cap
TIMEOUT = 60                        # per-request connect/read timeout, seconds
UA = "markitdown-skill-fetch/1.0"


# --------------------------------------------------------------------------- #
# Link-type handlers
# --------------------------------------------------------------------------- #

def _normalize(url: str) -> str:
    """Rewrite share links to direct-download form where a rewrite suffices."""
    # Dropbox: ?dl=0 (viewer page) -> ?dl=1 (direct file)
    if "dropbox.com" in url:
        if "dl=0" in url:
            return url.replace("dl=0", "dl=1")
        if "dl=1" not in url:
            sep = "&" if "?" in url else "?"
            return url + sep + "dl=1"
    return url


_GDRIVE_ID_RE = re.compile(r"drive\.google\.com/(?:file/d/([\w-]+)|open\?id=([\w-]+)|uc\?.*id=([\w-]+))")


def _gdrive_id(url: str) -> str | None:
    m = _GDRIVE_ID_RE.search(url)
    if not m:
        return None
    return next(g for g in m.groups() if g)


def _yadisk_href(url: str) -> str:
    """Resolve a public Yandex Disk link to a direct download href."""
    api = ("https://cloud-api.yandex.net/v1/disk/public/resources/download"
           "?public_key=" + urllib.parse.quote(url, safe=""))
    req = urllib.request.Request(api, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    href = data.get("href")
    if not href:
        raise RuntimeError(f"Yandex Disk API returned no download href: {data}")
    return href


_HTML_MARKERS = (b"<!doctype html", b"<html", b"<HTML", b"<!DOCTYPE html")


def _looks_like_html(first_bytes: bytes) -> bool:
    head = first_bytes.lstrip()[:64]
    return any(head.startswith(m) or m in head[:32] for m in _HTML_MARKERS)


def _extract_json_object(text: str, key: str) -> dict | None:
    """Extract and parse the balanced ``{...}`` following ``"key":`` in text.

    The Mail.ru page embeds a huge JS object that is not strictly valid JSON
    (it can contain JS-only escapes), so parsing the whole thing fails.
    Instead we cut out just the sub-object we need with a brace scanner and
    neutralize invalid escapes if strict parsing still complains.
    """
    m = re.search(r'"%s"\s*:\s*\{' % re.escape(key), text)
    if not m:
        return None
    i = m.end() - 1  # position of the opening brace
    depth, in_str, esc = 0, False, False
    for j in range(i, min(len(text), i + 2_000_000)):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    raw = text[i:j + 1]
                    try:
                        return json.loads(raw)
                    except json.JSONDecodeError:
                        fixed = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", raw)
                        try:
                            return json.loads(fixed)
                        except json.JSONDecodeError:
                            return None
    return None


def _ep_url(dispatcher, name: str) -> str | None:
    """Endpoint URL from a dispatcher block ({'url':..} or [{'url':..}, ...])."""
    v = (dispatcher or {}).get(name)
    if isinstance(v, list):
        v = v[0] if v else None
    if isinstance(v, dict):
        return v.get("url")
    return None


def _download_mailru(url: str, out_dir: Path) -> Path:
    """Mail.ru Cloud public/stock links (cloud.mail.ru/public/..., /stock/...).

    The share page is a JS app, so a plain GET returns a useless HTML shell —
    but it embeds `window.cloudSettings = {...}` with everything we need:
    the per-file ids (`weblink` for /public/, `stock` for /stock/), the real
    file name, and a `dispatcher` block naming the download servers
    (`weblink_get` for public links, `stock` for stock links).
    """
    import http.cookiejar

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [("User-Agent", UA)]

    with opener.open(url, timeout=TIMEOUT) as resp:
        page = resp.read(8 << 20).decode("utf-8", "replace")

    dispatcher = _extract_json_object(page, "dispatcher") or {}
    if not dispatcher:
        try:
            data = json.loads(opener.open(
                "https://cloud.mail.ru/api/v2/dispatcher?api=2",
                timeout=TIMEOUT).read().decode("utf-8"))
            dispatcher = data.get("body", {})
        except Exception:  # noqa: BLE001 - page block is the primary source
            pass
    stock_url = _ep_url(dispatcher, "stock")
    weblink_get = _ep_url(dispatcher, "weblink_get")

    ssf = _extract_json_object(page, "serverSideFolders") or {}
    folder = ssf.get("folder") if isinstance(ssf.get("folder"), dict) else None
    if folder is None:
        folder = _extract_json_object(page, "folder") or {}
    items = folder.get("list") or []
    bundle = folder.get("bundle") or ""
    files = [it for it in items
             if isinstance(it, dict) and it.get("name")
             and it.get("kind", "file") != "folder"]

    if not files:
        # Last resort: pull name+id pairs straight out of the raw page text.
        for pat in (r'"name":"([^"]+)"[^{}]*?"stock":"([^"]+)"',
                    r'"stock":"([^"]+)"[^{}]*?"name":"([^"]+)"',
                    r'"name":"([^"]+)"[^{}]*?"weblink":"([^"]+)"'):
            m = re.search(pat, page)
            if m:
                a, b = m.group(1), m.group(2)
                if "stock" in pat and pat.startswith(r'"stock"'):
                    files = [{"name": b, "stock": a}]
                elif "stock" in pat:
                    files = [{"name": a, "stock": b}]
                else:
                    files = [{"name": a, "weblink": b}]
                break
    if not files:
        raise RuntimeError("Mail.ru Cloud: no files found in the page state "
                           "(empty share, or the link is not public)")

    last_err: Exception | None = None
    for it in files:
        name = Path(str(it["name"])).name
        qname = urllib.parse.quote(name)
        candidates: list[str] = []
        if it.get("stock") and stock_url:
            sid = urllib.parse.quote(str(it["stock"]), safe="/")
            candidates += [f"{stock_url.rstrip('/')}/{sid}/{qname}",
                           f"{stock_url.rstrip('/')}/{sid}"]
        if bundle and stock_url:
            b = urllib.parse.quote(str(bundle), safe="/")
            candidates.append(f"{stock_url.rstrip('/')}/{b}/{qname}")
        if it.get("weblink") and weblink_get:
            w = urllib.parse.quote(str(it["weblink"]), safe="/")
            candidates.append(f"{weblink_get.rstrip('/')}/{w}")

        for dl in candidates:
            try:
                with opener.open(dl, timeout=TIMEOUT) as resp:
                    first = resp.read(1024)
                    if not first or _looks_like_html(first):
                        continue  # got a web page back, not the file
                    dest = out_dir / name
                    with open(dest, "wb") as fh:
                        fh.write(first)
                        total = len(first)
                        while True:
                            chunk = resp.read(1 << 20)
                            if not chunk:
                                break
                            total += len(chunk)
                            if total > MAX_BYTES:
                                raise RuntimeError(
                                    f"file exceeds {MAX_BYTES // (1 << 30)} GB cap")
                            fh.write(chunk)
                    return dest
            except Exception as exc:  # noqa: BLE001 - try the next candidate
                last_err = exc

    raise RuntimeError(
        "Mail.ru Cloud: could not download "
        f"({len(files)} file(s) found, e.g. '{files[0]['name']}'; "
        f"last error: {last_err}). Make sure the link is public.")


# --------------------------------------------------------------------------- #
# Download
# --------------------------------------------------------------------------- #

def _filename_from_response(resp, url: str) -> str:
    cd = resp.headers.get("Content-Disposition", "")
    m = re.search(r"filename\*=(?:UTF-8'')?\"?([^\";]+)", cd) or \
        re.search(r'filename="?([^";]+)', cd)
    if m:
        name = urllib.parse.unquote(m.group(1)).strip()
        if name:
            return Path(name).name
    # Yandex hrefs carry the real name in a query param.
    q = urllib.parse.parse_qs(urllib.parse.urlparse(resp.url or url).query)
    if q.get("filename"):
        return Path(q["filename"][0]).name
    name = Path(urllib.parse.urlparse(url).path).name
    if name and "." in name:
        return name
    ext = mimetypes.guess_extension(
        (resp.headers.get("Content-Type") or "").split(";")[0].strip()) or ".bin"
    return f"download_{int(time.time())}{ext}"


def _stream_to(resp, dest: Path) -> int:
    total = 0
    with open(dest, "wb") as fh:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise RuntimeError(f"file exceeds {MAX_BYTES // (1 << 30)} GB cap")
            fh.write(chunk)
    return total


def _download_plain(url: str, out_dir: Path) -> Path:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        name = _filename_from_response(resp, url)
        dest = out_dir / name
        _stream_to(resp, dest)
    return dest


def _download_gdrive(url: str, out_dir: Path) -> Path:
    file_id = _gdrive_id(url)
    try:
        import gdown  # handles the "file too large to scan" confirm flow
        out = gdown.download(id=file_id, output=str(out_dir) + "/", quiet=True,
                             fuzzy=True) if file_id else \
              gdown.download(url=url, output=str(out_dir) + "/", quiet=True,
                             fuzzy=True)
        if not out:
            raise RuntimeError("gdown could not download the file "
                               "(is the link shared as 'anyone with the link'?)")
        return Path(out)
    except ImportError:
        if not file_id:
            raise RuntimeError("unrecognized Google Drive link and gdown "
                               "is not installed (pip install gdown)")
        return _download_plain(
            f"https://drive.google.com/uc?export=download&id={file_id}", out_dir)


def download(url: str, out_dir: Path) -> Path:
    url = _normalize(url.strip())
    if "drive.google.com" in url:
        return _download_gdrive(url, out_dir)
    if "disk.yandex." in url or "yadi.sk" in url:
        return _download_plain(_yadisk_href(url), out_dir)
    if "cloud.mail.ru" in url:
        return _download_mailru(url, out_dir)
    return _download_plain(url, out_dir)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def _read_links(path: Path) -> list[str]:
    if not path.is_file():
        return []
    links = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line.lower().startswith(("http://", "https://")):
            links.append(line)
    return links


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Download files from a links file for conversion.")
    ap.add_argument("links_file", nargs="?", help="file with one URL per line")
    ap.add_argument("--url", action="append", default=[],
                    help="download a single URL (repeatable)")
    ap.add_argument("--out", required=True, help="directory for downloads")
    ap.add_argument("--state", help="JSON file tracking already-processed URLs")
    ap.add_argument("--refetch", action="store_true",
                    help="ignore the state file and download everything again")
    args = ap.parse_args(argv)

    urls = list(args.url)
    if args.links_file:
        urls.extend(_read_links(Path(args.links_file)))
    if not urls:
        return 0  # nothing to do is fine

    state_path = Path(args.state) if args.state else None
    state: dict = {}
    if state_path and state_path.is_file() and not args.refetch:
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state = {}

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for url in urls:
        if url in state:
            continue
        try:
            dest = download(url, out_dir)
            print(dest)
            state[url] = {"file": dest.name, "ts": int(time.time())}
        except Exception as exc:  # noqa: BLE001 - report and move on
            failures += 1
            print(f"error: {url}: {exc}", file=sys.stderr)

    if state_path:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
