#!/usr/bin/env python3
"""Generate index.html: one breeding-path link per Pal, carrying the Pals I own.

    python3 build_site.py                # write ./index.html, to preview locally
    python3 build_site.py --out _site    # write into a dir, as CI does before deploying

Every Pal in data/pals.json gets a link with itself as the target and the Pals
checked off in pals.md as the `own` list. Published via GitHub Pages.
"""

import argparse
import html
import json
import shutil
import sys
from pathlib import Path

from breeding_path import build_url, load_data, load_owned, load_pals, load_wanted

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"

PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Palworld breeding paths</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #fbfaf8; --fg: #1a1a19; --muted: #6b6b66;
    --card: #fff; --line: #e5e3de; --accent: #2f6f4f; --owned: #eef4f0;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #16171a; --fg: #e8e8e6; --muted: #90918d;
      --card: #1f2125; --line: #2e3136; --accent: #7fd0a3; --owned: #1b2a22;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 2rem 1.25rem 4rem;
    background: var(--bg); color: var(--fg);
    font: 16px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  }}
  header, .tools, ul, section.wanted, hr, .empty, footer {{ max-width: 74rem; margin-inline: auto; }}
  header {{ margin-bottom: 1.5rem; }}
  h1 {{ margin: 0 0 .25rem; font-size: 1.6rem; letter-spacing: -.01em; }}
  p.sub {{ margin: 0; color: var(--muted); font-size: .9rem; }}

  .tools {{ display: flex; gap: .6rem; flex-wrap: wrap; margin-bottom: 1.25rem; }}
  input[type=search], select {{
    padding: .55rem .75rem; font-size: 1rem; font-family: inherit;
    background: var(--card); color: var(--fg);
    border: 1px solid var(--line); border-radius: .5rem;
  }}
  input[type=search] {{ flex: 1 1 14rem; }}
  input[type=search]:focus, select:focus {{ outline: 2px solid var(--accent); outline-offset: 1px; }}
  label.toggle {{
    display: flex; align-items: center; gap: .4rem;
    padding: .55rem .75rem; font-size: .9rem; color: var(--muted);
    background: var(--card); border: 1px solid var(--line); border-radius: .5rem;
    cursor: pointer; user-select: none;
  }}

  ul {{
    padding: 0; list-style: none; display: grid; gap: .5rem;
    grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr));
  }}
  li.hidden {{ display: none; }}
  a {{
    display: flex; align-items: center; gap: .6rem;
    padding: .5rem .6rem; text-decoration: none; color: inherit;
    background: var(--card); border: 1px solid var(--line); border-radius: .5rem;
  }}
  a:hover, a:focus-visible {{ border-color: var(--accent); outline: none; }}
  li.owned a {{ background: var(--owned); }}

  img.pal {{ width: 40px; height: 40px; flex: none; image-rendering: -webkit-optimize-contrast; }}
  .body {{ min-width: 0; flex: 1; }}
  .top {{ display: flex; align-items: baseline; gap: .4rem; }}
  .name {{ font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .num {{ font-size: .72rem; color: var(--muted); font-variant-numeric: tabular-nums; flex: none; }}
  .tag {{ font-size: .68rem; color: var(--accent); margin-left: auto; flex: none; }}
  .meta {{ display: flex; align-items: center; gap: .5rem; margin-top: .15rem; flex-wrap: wrap; }}
  .elems {{ display: flex; gap: .15rem; }}
  .elems img {{ width: 15px; height: 15px; }}
  .work {{ display: flex; gap: .3rem; flex-wrap: wrap; }}
  .w {{ display: inline-flex; align-items: center; gap: .1rem; font-size: .7rem; color: var(--muted); }}
  .w img {{ width: 14px; height: 14px; opacity: .85; }}

  section.wanted {{ margin-bottom: 2rem; }}
  h2 {{
    margin: 0 0 .6rem; font-size: .78rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: .08em; color: var(--muted);
  }}
  section.wanted a {{ border-color: var(--accent); }}
  hr {{ border: 0; border-top: 1px solid var(--line); margin-bottom: 1.5rem; }}
  .empty {{ margin: 2rem auto; color: var(--muted); }}
  footer {{ margin-top: 3rem; color: var(--muted); font-size: .8rem; }}
  footer a {{
    display: inline; padding: 0; background: none; border: none;
    color: var(--accent); text-decoration: underline;
  }}
</style>

<header>
  <h1>Palworld breeding paths</h1>
  <p class="sub">
    Every Pal, linked to its shortest breeding path from the {owned_count} Pals I own.
    Clicking a Pal I already have shows how to breed <em>another</em> one.
  </p>
</header>

{wanted_section}
<div class="tools">
  <input type="search" id="q" placeholder="Filter Pals&hellip;" autofocus aria-label="Filter Pals">
  <select id="element" aria-label="Filter by element">
    <option value="">Any element</option>
{element_options}
  </select>
  <select id="work" aria-label="Filter by work suitability">
    <option value="">Any work</option>
{work_options}
  </select>
  <select id="sort" aria-label="Sort by">
    <option value="name">Sort: name</option>
    <option value="index">Sort: number</option>
    <option value="element">Sort: element</option>
    <option value="work">Sort: work level</option>
  </select>
  <label class="toggle"><input type="checkbox" id="hide-owned"> Hide Pals I own</label>
</div>

<ul id="list">
{items}
</ul>
<p class="empty hidden" id="empty">No Pals match those filters.</p>

<footer>
  Breeding paths resolved by <a href="https://palworld.gg/breeding-path">palworld.gg</a>,
  whose Pal data and icons this page reuses. Not affiliated with palworld.gg or Pocketpair.
</footer>

<script>
  const q = document.getElementById('q');
  const elementSel = document.getElementById('element');
  const workSel = document.getElementById('work');
  const sortSel = document.getElementById('sort');
  const hideOwned = document.getElementById('hide-owned');
  const list = document.getElementById('list');
  const empty = document.getElementById('empty');

  const items = [...list.querySelectorAll('li')].map(li => ({{
    li,
    name: li.dataset.name,
    index: +li.dataset.index,          // -1 for Pals with no Paldeck number
    elements: li.dataset.elements.split(',').filter(Boolean),
    work: JSON.parse(li.dataset.work),
    owned: li.classList.contains('owned'),
  }}));

  function apply() {{
    const needle = q.value.trim().toLowerCase();
    const element = elementSel.value;
    const work = workSel.value;

    let shown = 0;
    for (const it of items) {{
      const match = it.name.includes(needle)
        && (!element || it.elements.includes(element))
        && (!work || work in it.work)
        && !(hideOwned.checked && it.owned);
      it.li.classList.toggle('hidden', !match);
      if (match) shown++;
    }}
    empty.classList.toggle('hidden', shown > 0);

    // Sorting by work level means the level of the work you filtered on, if any —
    // "best miners first". With no work filter, fall back to total work level.
    const total = it => Object.values(it.work).reduce((a, b) => a + b, 0);
    const byName = (a, b) => a.name.localeCompare(b.name);
    const sorters = {{
      name: byName,
      // Pals with no Paldeck number (the Terraria crossovers) sort last, not first.
      index: (a, b) => (a.index < 0) - (b.index < 0) || a.index - b.index || byName(a, b),
      element: (a, b) => (a.elements[0] || '').localeCompare(b.elements[0] || '') || byName(a, b),
      work: (a, b) => (work ? (b.work[work] || 0) - (a.work[work] || 0)
                            : total(b) - total(a)) || byName(a, b),
    }};

    const order = [...items].sort(sorters[sortSel.value]);
    list.append(...order.map(it => it.li));
  }}

  for (const el of [q, elementSel, workSel, sortSel, hideOwned]) {{
    el.addEventListener('input', apply);
  }}
  apply();
</script>
"""


def icons_html(pal: dict, data: dict) -> str:
    elems = "".join(
        f'<img src="assets/icons/{data["elements"][e]["icon"]}.png" '
        f'alt="{html.escape(e)}" title="{html.escape(e)}" width="15" height="15">'
        for e in pal["elements"]
    )
    work = "".join(
        f'<span class=w><img src="assets/icons/{data["work"][w]}.png" '
        f'alt="" title="{html.escape(w)}" width="14" height="14">{lvl}</span>'
        for w, lvl in sorted(pal["work"].items(), key=lambda kv: (-kv[1], kv[0]))
    )
    return (
        f'<span class=elems>{elems}</span>'
        f'{f"<span class=work>{work}</span>" if work else ""}'
    )


def card(pal: dict, data: dict, owned: list[str]) -> str:
    """One Pal, linked to its breeding path from the Pals owned.

    A Pal you already have is excluded from its own `own` list — otherwise the
    site answers "0 breeds away, you have it", which is useless when the point
    is to breed a second one.
    """
    name, pal_id = pal["name"], pal["id"]
    is_owned = pal_id in set(owned)
    parents = [i for i in owned if i != pal_id]
    number = f'<span class=num>#{pal["index"]}</span>' if pal["index"] > 0 else ""

    return (
        f'  <li class="{"owned" if is_owned else ""}"'
        f' data-name="{html.escape(name.lower(), quote=True)}"'
        f' data-index="{pal["index"]}"'
        f' data-elements="{html.escape(",".join(pal["elements"]), quote=True)}"'
        f" data-work='{html.escape(json.dumps(pal['work']), quote=True)}'>"
        f'<a href="{html.escape(build_url(pal_id, parents), quote=True)}"'
        f' target="_blank" rel="noopener">'
        f'<img class=pal src="assets/pals/{pal["icon"]}.png" alt="" width="40" height="40" loading="lazy">'
        f'<span class=body>'
        f'<span class=top><span class=name>{html.escape(name)}</span>{number}'
        f'{"<span class=tag>owned</span>" if is_owned else ""}</span>'
        f'<span class=meta>{icons_html(pal, data)}</span>'
        f"</span></a></li>"
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT,
        metavar="DIR",
        help="directory to write index.html into (default: repo root)",
    )
    args = ap.parse_args()

    data = load_data()
    name_to_id = load_pals()
    owned = load_owned(name_to_id)
    wanted = load_wanted(name_to_id)
    if not owned:
        sys.exit("no Pals are checked off in pals.md")

    by_name = {p["name"]: p for p in data["pals"]}

    # Wanted Pals keep their file order — it is a hand-written priority list.
    # Owned ones stay in the section, tagged the same way as everywhere else.
    wanted_section = ""
    if wanted:
        cards = "\n".join(card(by_name[name], data, owned) for name, _ in wanted)
        wanted_section = (
            f"<section class=wanted>\n  <h2>Wanted</h2>\n  <ul>\n{cards}\n  </ul>\n</section>\n<hr>"
        )

    items = "\n".join(
        card(p, data, owned) for p in sorted(data["pals"], key=lambda p: p["name"])
    )
    options = lambda keys: "\n".join(
        f'    <option value="{html.escape(k, quote=True)}">{html.escape(k)}</option>'
        for k in sorted(keys)
    )

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(
        PAGE.format(
            owned_count=len(owned),
            wanted_section=wanted_section,
            element_options=options(data["elements"]),
            work_options=options(data["work"]),
            items=items,
        )
    )

    if out_dir.resolve() != ROOT.resolve():
        shutil.copytree(ASSETS, out_dir / "assets", dirs_exist_ok=True)

    print(
        f"wrote {out_dir / 'index.html'}: {len(data['pals'])} links, "
        f"{len(owned)} owned, {len(wanted)} wanted",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
