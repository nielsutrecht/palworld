#!/usr/bin/env python3
"""Generate index.html: one breeding-path link per Pal, carrying the Pals I own.

    python3 build_site.py

Every Pal in data/pals.json gets a link with itself as the target and the Pals
checked off in pals.md as the `own` list. Published via GitHub Pages.
"""

import html
import sys
from pathlib import Path

from breeding_path import build_url, load_owned, load_pals

ROOT = Path(__file__).parent
OUT = ROOT / "index.html"

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
  header {{ max-width: 62rem; margin: 0 auto 1.5rem; }}
  h1 {{ margin: 0 0 .25rem; font-size: 1.6rem; letter-spacing: -.01em; }}
  p.sub {{ margin: 0; color: var(--muted); font-size: .9rem; }}
  .tools {{ max-width: 62rem; margin: 0 auto 1.25rem; display: flex; gap: .6rem; flex-wrap: wrap; }}
  input[type=search] {{
    flex: 1 1 16rem; padding: .55rem .75rem; font-size: 1rem;
    background: var(--card); color: var(--fg);
    border: 1px solid var(--line); border-radius: .5rem;
  }}
  input[type=search]:focus {{ outline: 2px solid var(--accent); outline-offset: 1px; }}
  label.toggle {{
    display: flex; align-items: center; gap: .4rem;
    padding: .55rem .75rem; font-size: .9rem; color: var(--muted);
    background: var(--card); border: 1px solid var(--line); border-radius: .5rem;
    cursor: pointer; user-select: none;
  }}
  ul {{
    max-width: 62rem; margin: 0 auto; padding: 0; list-style: none;
    display: grid; gap: .5rem;
    grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr));
  }}
  li.hidden {{ display: none; }}
  a {{
    display: flex; align-items: center; justify-content: space-between; gap: .5rem;
    padding: .6rem .75rem; text-decoration: none; color: inherit;
    background: var(--card); border: 1px solid var(--line); border-radius: .5rem;
  }}
  a:hover, a:focus-visible {{ border-color: var(--accent); outline: none; }}
  li.owned a {{ background: var(--owned); }}
  .tag {{ font-size: .72rem; color: var(--accent); flex: none; }}
  .empty {{ max-width: 62rem; margin: 2rem auto; color: var(--muted); }}
  footer {{ max-width: 62rem; margin: 3rem auto 0; color: var(--muted); font-size: .8rem; }}
  footer a {{
    display: inline; padding: 0; background: none; border: none;
    color: var(--accent); text-decoration: underline;
  }}
</style>

<header>
  <h1>Palworld breeding paths</h1>
  <p class="sub">
    Every Pal, linked to its shortest breeding path from the {owned_count} Pals I own.
    Generated from <code>pals.md</code> &mdash; {total} Pals.
  </p>
</header>

<div class="tools">
  <input type="search" id="q" placeholder="Filter Pals&hellip;" autofocus aria-label="Filter Pals">
  <label class="toggle"><input type="checkbox" id="hide-owned"> Hide Pals I own</label>
</div>

<ul id="list">
{items}
</ul>
<p class="empty hidden" id="empty">No Pals match that filter.</p>

<footer>
  Breeding paths resolved by <a href="https://palworld.gg/breeding-path">palworld.gg</a>,
  which is not affiliated with this page.
</footer>

<script>
  const q = document.getElementById('q');
  const hideOwned = document.getElementById('hide-owned');
  const empty = document.getElementById('empty');
  const items = [...document.querySelectorAll('#list li')];

  function apply() {{
    const needle = q.value.trim().toLowerCase();
    let shown = 0;
    for (const li of items) {{
      const match = li.dataset.name.includes(needle)
        && !(hideOwned.checked && li.classList.contains('owned'));
      li.classList.toggle('hidden', !match);
      if (match) shown++;
    }}
    empty.classList.toggle('hidden', shown > 0);
  }}

  q.addEventListener('input', apply);
  hideOwned.addEventListener('change', apply);
</script>
"""


def main() -> None:
    name_to_id = load_pals()
    owned = load_owned(name_to_id)
    if not owned:
        sys.exit("no Pals are checked off in pals.md")

    owned_ids = set(owned)
    items = []
    for name, pal_id in sorted(name_to_id.items()):
        is_owned = pal_id in owned_ids
        safe_name = html.escape(name)
        items.append(
            f'  <li class="{"owned" if is_owned else ""}" data-name="{html.escape(name.lower(), quote=True)}">'
            f'<a href="{html.escape(build_url(pal_id, owned), quote=True)}">'
            f"<span>{safe_name}</span>"
            f'{"<span class=tag>owned</span>" if is_owned else ""}'
            f"</a></li>"
        )

    OUT.write_text(
        PAGE.format(
            owned_count=len(owned),
            total=len(name_to_id),
            items="\n".join(items),
        )
    )
    print(f"wrote {OUT}: {len(name_to_id)} links, {len(owned)} Pals owned", file=sys.stderr)


if __name__ == "__main__":
    main()
