#!/usr/bin/env python3
"""Build a palworld.gg breeding-path URL from the Pals checked off in pals.md.

    python3 breeding_path.py Anubis
    python3 breeding_path.py "Blazamut Ryu" --open

The site takes internal Pal ids, not display names or its own url slugs, so
names are resolved through data/pals.json. See CLAUDE.md.
"""

import argparse
import difflib
import json
import re
import sys
import urllib.parse
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent
PALS_MD = ROOT / "pals.md"
PALS_JSON = ROOT / "data" / "pals.json"
ENDPOINT = "https://palworld.gg/breeding-path"

CHECKBOX = re.compile(r"^\s*[-*]\s*\[(?P<mark>[ xX])\]\s*(?P<name>.+?)\s*$")


def load_pals() -> dict[str, str]:
    if not PALS_JSON.exists():
        sys.exit(f"{PALS_JSON} is missing; run: python3 refresh_pals.py")
    pals = json.loads(PALS_JSON.read_text())
    return {p["name"]: p["id"] for p in pals}


def load_owned(name_to_id: dict[str, str]) -> list[str]:
    """Return ids of the Pals checked off in pals.md, in file order."""
    owned, unknown = [], []
    for lineno, line in enumerate(PALS_MD.read_text().splitlines(), 1):
        m = CHECKBOX.match(line)
        if not m or m["mark"] == " ":
            continue
        name = m["name"]
        if name not in name_to_id:
            unknown.append(f"  pals.md:{lineno}: {name}")
            continue
        owned.append(name_to_id[name])

    if unknown:
        sys.exit(
            "these checked Pals are not in data/pals.json (typo, or the Pal is not "
            "breedable):\n" + "\n".join(unknown)
        )
    return owned


def resolve_target(target: str, name_to_id: dict[str, str]) -> str:
    if target in name_to_id:
        return name_to_id[target]

    folded = {n.casefold(): n for n in name_to_id}
    if target.casefold() in folded:
        return name_to_id[folded[target.casefold()]]

    near = [n for n in name_to_id if target.casefold() in n.casefold()]
    near = near or difflib.get_close_matches(target, name_to_id, n=5, cutoff=0.6)
    hint = f"\ndid you mean: {', '.join(sorted(near)[:8])}" if near else ""
    sys.exit(f"unknown target Pal: {target}{hint}")


def build_url(target_id: str, owned: list[str]) -> str:
    # Keep commas literal, as the site's own links do.
    query = urllib.parse.urlencode(
        {"target": target_id, "own": ",".join(owned)}, safe=","
    )
    return f"{ENDPOINT}?{query}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="display name of the Pal you want to breed")
    ap.add_argument("--open", action="store_true", help="open the URL in a browser")
    args = ap.parse_args()

    name_to_id = load_pals()
    target_id = resolve_target(args.target, name_to_id)
    owned = load_owned(name_to_id)

    if not owned:
        sys.exit("no Pals are checked off in pals.md")
    if target_id in owned:
        print(f"note: you already own {args.target}", file=sys.stderr)

    url = build_url(target_id, owned)

    print(f"{len(owned)} Pals owned", file=sys.stderr)
    print(url)
    if args.open:
        webbrowser.open(url)


if __name__ == "__main__":
    main()
