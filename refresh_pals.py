#!/usr/bin/env python3
"""Regenerate data/pals.json and assets/ from palworld.gg's bundled Pal data.

The data lives in a hashed Vite chunk whose URL changes on every site rebuild,
so we rediscover it from the page each time rather than hardcoding the hash.
See CLAUDE.md for the shape of the data.

Icons are vendored into assets/ rather than hotlinked, so the published page
does not lean on palworld.gg's bandwidth or survive only as long as their paths
do. Already-downloaded icons are skipped, so reruns are cheap.
"""

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://palworld.gg"
PAGE = f"{BASE}/breeding-path"
ROOT = Path(__file__).parent
OUT = ROOT / "data" / "pals.json"
PAL_ICONS = ROOT / "assets" / "pals"
UI_ICONS = ROOT / "assets" / "icons"

# palworld.gg serves a resized variant through its image proxy; the full-size
# icons are ~10 KB each, these are ~3 KB, and nothing is displayed above 60px.
PAL_ICON_URL = f"{BASE}/_ipx/q_80&s_60x60/images/full_palicon/{{icon}}.png"
UI_ICON_URL = f"{BASE}/images/icons/{{icon}}.png"

# Maps element/work names to their icon (and element colour), as the site does.
ELEMENT_RE = re.compile(
    r'(?P<name>\w+):\{image:"(?P<icon>T_Icon_element_s_\d+)",label:"\w+",color:"(?P<color>#[0-9a-fA-F]+)"\}'
)
WORK_RE = re.compile(r'(?P<name>\w+):\{image:"(?P<icon>T_icon_palwork_\d+)",label:"\w+"\}')


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def get_text(url: str) -> str:
    return get(url).decode("utf-8")


def chunks_on(page_url: str) -> list[str]:
    page = get_text(page_url)
    return sorted(set(re.findall(r"/_nuxt/[A-Za-z0-9_-]+\.js", page)))


def find_data(chunk_urls: list[str]) -> tuple[str, dict, dict]:
    """Find the Pal data chunk, the element map and the work map."""
    pal_js, elements, work = None, {}, {}

    for chunk in chunk_urls:
        js = get_text(BASE + chunk)

        if not pal_js:
            m = re.search(
                r'"\.\./data/pals/en\.json"\s*:\s*\(\)\s*=>\s*\w+\(\(\)\s*=>\s*import\("\./([A-Za-z0-9_-]+\.js)"',
                js,
            )
            if m:
                pal_js = get_text(f"{BASE}/_nuxt/{m.group(1)}")

        if not elements:
            elements = {
                m["name"]: {"icon": m["icon"], "color": m["color"]}
                for m in ELEMENT_RE.finditer(js)
            }
        if not work:
            work = {m["name"]: m["icon"] for m in WORK_RE.finditer(js)}

    if not pal_js:
        sys.exit("could not find the ../data/pals/en.json import map; site layout changed?")
    if not elements or not work:
        sys.exit("could not find the element/work icon maps; site layout changed?")
    return pal_js, elements, work


def iter_objects(js: str):
    """Yield the source text of each top-level `{id:"..."` object literal.

    Brace-matches while skipping over string literals, since descriptions are
    template literals that can contain braces and newlines.
    """
    for start in (m.start() for m in re.finditer(r'\{id:"', js)):
        depth, i, n = 0, start, len(js)
        while i < n:
            c = js[i]
            if c in "\"'`":
                quote, i = c, i + 1
                while i < n:
                    if js[i] == "\\":
                        i += 2
                        continue
                    if js[i] == quote:
                        break
                    i += 1
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    yield js[start : i + 1]
                    break
            i += 1


def field(obj: str, name: str):
    m = re.search(rf'\b{name}:"((?:[^"\\]|\\.)*)"', obj)
    if m:
        return m.group(1)
    # Booleans first: `!0`/`!1` are minified true/false. The number branch must be
    # whole — an alternation starting with [01] would match `index:139` as just `1`.
    m = re.search(rf"\b{name}:(!0|!1|-?\d+(?:\.\d+)?(?:e\d+)?)", obj)
    if not m:
        return None
    v = m.group(1)
    if v in ("!0", "!1"):
        return v == "!0"
    return float(v) if ("." in v or "e" in v) else int(v)


def elements_of(obj: str) -> list[str]:
    m = re.search(r"\belements:\[([^\]]*)\]", obj)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


def work_of(obj: str) -> dict[str, int]:
    m = re.search(r"\bwork:\{([^}]*)\}", obj)
    if not m:
        return {}
    return {k: int(v) for k, v in re.findall(r'"?(\w+)"?:(\d+)', m.group(1))}


def download_icons(icons: set[str], dest: Path, url_tpl: str, what: str) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    missing = sorted(i for i in icons if not (dest / f"{i}.png").exists())
    if not missing:
        print(f"{what}: {len(icons)} already present", file=sys.stderr)
        return

    print(f"{what}: downloading {len(missing)} of {len(icons)}", file=sys.stderr)
    for n, icon in enumerate(missing, 1):
        # The proxy path contains a literal `&`, which is part of the path, not a query.
        url = url_tpl.format(icon=urllib.parse.quote(icon))
        (dest / f"{icon}.png").write_bytes(get(url))
        if n % 50 == 0 or n == len(missing):
            print(f"  {n}/{len(missing)}", file=sys.stderr)


def main() -> None:
    pal_js, elements, work_icons = find_data(chunks_on(PAGE))
    print(f"{len(elements)} elements, {len(work_icons)} work types", file=sys.stderr)

    by_id = {}
    for obj in iter_objects(pal_js):
        pal_id = field(obj, "id")
        if not pal_id or pal_id in by_id:
            continue

        combos = re.search(r"\bcombos:\[(.*?)\](?=,\w+:|\})", obj, re.S)
        by_id[pal_id] = {
            "id": pal_id,
            "slug": field(obj, "slug"),
            # Some upstream names carry stray whitespace ("Tetroise "); strip it, or the
            # name won't match a checkbox in pals.md, whose parser trims trailing space.
            "name": (field(obj, "name") or "").strip() or None,
            "index": field(obj, "index"),
            "icon": field(obj, "icon"),
            "elements": elements_of(obj),
            "work": work_of(obj),
            "isBoss": field(obj, "isBoss"),
            "combiRank": field(obj, "combiRank"),
            "ignoreCombi": field(obj, "ignoreCombi"),
            "hasCombos": bool(combos and combos.group(1).strip()),
        }

    def breedable(p) -> bool:
        return bool(
            p["name"]
            and p["icon"]
            and not p["isBoss"]
            and p["combiRank"]
            and p["combiRank"] != 9999
            and not (p["ignoreCombi"] and not p["hasCombos"])
        )

    pals = [
        {k: p[k] for k in ("id", "name", "slug", "index", "icon", "elements", "work")}
        for p in sorted(by_id.values(), key=lambda p: p["name"] or "")
        if breedable(p)
    ]

    names = [p["name"] for p in pals]
    if dupes := {n for n in names if names.count(n) > 1}:
        sys.exit(f"display names are not unique, pals.md cannot key on them: {dupes}")

    # A new element or work type would otherwise render as a silently missing icon.
    for p in pals:
        if unknown := set(p["elements"]) - set(elements):
            sys.exit(f"{p['name']}: unknown element(s) {unknown}; update the element map")
        if unknown := set(p["work"]) - set(work_icons):
            sys.exit(f"{p['name']}: unknown work type(s) {unknown}; update the work map")

    print(f"{len(by_id)} unique ids, {len(pals)} breedable", file=sys.stderr)
    if len(pals) != 297:
        print(
            f"note: expected 297 breedable pals, got {len(pals)} "
            "(fine if Palworld added Pals; check the site's counter)",
            file=sys.stderr,
        )

    download_icons({p["icon"] for p in pals}, PAL_ICONS, PAL_ICON_URL, "pal icons")
    download_icons(
        {e["icon"] for e in elements.values()} | set(work_icons.values()),
        UI_ICONS,
        UI_ICON_URL,
        "ui icons",
    )

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(
        json.dumps(
            {"elements": elements, "work": work_icons, "pals": pals},
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(f"wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
