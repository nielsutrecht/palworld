#!/usr/bin/env python3
"""Regenerate data/pals.json from palworld.gg's bundled Pal data.

The data lives in a hashed Vite chunk whose URL changes on every site rebuild,
so we rediscover it from the page each time rather than hardcoding the hash.
See CLAUDE.md for the shape of the data.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

BASE = "https://palworld.gg"
PAGE = f"{BASE}/breeding-path"
OUT = Path(__file__).parent / "data" / "pals.json"


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def find_pal_chunk() -> str:
    """Locate the chunk that ../data/pals/en.json compiles to."""
    page = get(PAGE)
    chunks = sorted(set(re.findall(r"/_nuxt/[A-Za-z0-9_-]+\.js", page)))
    if not chunks:
        sys.exit("no /_nuxt/*.js chunks found on the page; site layout changed?")

    for chunk in chunks:
        js = get(BASE + chunk)
        m = re.search(
            r'"\.\./data/pals/en\.json"\s*:\s*\(\)\s*=>\s*\w+\(\(\)\s*=>\s*import\("\./([A-Za-z0-9_-]+\.js)"',
            js,
        )
        if m:
            return f"{BASE}/_nuxt/{m.group(1)}"

    sys.exit("could not find the ../data/pals/en.json import map; site layout changed?")


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
    m = re.search(rf"\b{name}:(!?[01]|\d+(?:\.\d+)?(?:e\d+)?)", obj)
    if not m:
        return None
    v = m.group(1)
    if v == "!0":
        return True
    if v == "!1":
        return False
    return float(v) if ("." in v or "e" in v) else int(v)


def main() -> None:
    url = find_pal_chunk()
    print(f"pal data chunk: {url}", file=sys.stderr)
    js = get(url)

    by_id = {}
    for obj in iter_objects(js):
        pal_id = field(obj, "id")
        if not pal_id or pal_id in by_id:
            continue

        # `combos` is a list of breeding recipes; we only need to know if it is empty.
        combos = re.search(r"\bcombos:\[(.*?)\](?=,\w+:|\})", obj, re.S)
        has_combos = bool(combos and combos.group(1).strip())

        by_id[pal_id] = {
            "id": pal_id,
            "slug": field(obj, "slug"),
            "name": field(obj, "name"),
            "icon": field(obj, "icon"),
            "isBoss": field(obj, "isBoss"),
            "combiRank": field(obj, "combiRank"),
            "ignoreCombi": field(obj, "ignoreCombi"),
            "hasCombos": has_combos,
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
        {"id": p["id"], "name": p["name"], "slug": p["slug"]}
        for p in sorted(by_id.values(), key=lambda p: p["name"] or "")
        if breedable(p)
    ]

    names = [p["name"] for p in pals]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        sys.exit(f"display names are not unique, pals.md cannot key on them: {dupes}")

    print(f"{len(by_id)} unique ids, {len(pals)} breedable", file=sys.stderr)
    if len(pals) != 297:
        print(
            f"warning: expected 297 breedable pals, got {len(pals)} "
            "(fine if Palworld added Pals; check the site's counter)",
            file=sys.stderr,
        )

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(pals, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
