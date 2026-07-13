# Palworld breeding helper

Generates a [palworld.gg breeding-path](https://palworld.gg/breeding-path) link from a
markdown file that tracks which Pals I own, so the site can compute the shortest breeding
chain to a target Pal.

## The URL contract

```
https://palworld.gg/breeding-path?target=<id>&own=<id>,<id>,...
```

Both `target` and `own` take **internal Pal ids**, not display names and not the site's own
url slugs. The three differ, and the difference is not mechanical:

| id (use this)  | slug         | display name |
| -------------- | ------------ | ------------ |
| `sheepball`    | `lamball`    | Lamball      |
| `clionetwins`  | `amione`     | Amione       |
| `flamebuffalo` | `arsox`      | Arsox        |
| `anubis`       | `anubis`     | Anubis       |

Some ids happen to equal the slug (`anubis`), which makes it easy to wrongly assume the
param is a slug. It isn't. Always resolve through the id map.

The site renders the result client-side, so `curl`/WebFetch on the URL returns an empty
shell. To read a generated link, drive it with a real browser (`playwright-cli open <url>`
then `playwright-cli eval "document.body.innerText"`) and look for the `BREEDING PLAN`
section.

## Pal data

Source of truth is palworld.gg's own bundled Pal data. It is not a stable public endpoint —
it is a hashed Vite chunk, so the URL changes on every site rebuild. Rediscover it rather
than hardcoding the hash:

1. `curl -s https://palworld.gg/breeding-path` → find the `/_nuxt/*.js` entry chunk.
2. Grep the chunks for `../data/pals/en.json` → it maps to a hashed chunk name
   (was `CK2A4_hG.js`), which is an ES module exporting one object per Pal.
3. Each object has `id`, `slug`, `name`, `combos`, `combiRank`, `isBoss`, `ignoreCombi`.

Pals are exported under two aliases each, so dedupe by `id` before counting.

The site's breedable set (its `297 / 297` counter) is:

```js
p.name && p.icon && !p.isBoss && p.combiRank && p.combiRank != 9999
  && !(p.ignoreCombi && !(p.combos || []).length)
```

That yields 297 breedable Pals out of 299 unique ids. Display names are **unique** within
that set, so a display-name → id map is unambiguous and safe to key the tracking file on.

## Layout

- `pals.md` — the tracking file. One checkbox per breedable Pal, keyed by display name;
  checked = owned. **The only file you edit by hand.**
- `data/pals.json` — generated `{id, name, slug}` map. Do not hand-edit.
- `refresh_pals.py` — regenerates `data/pals.json` from the site.
- `breeding_path.py` — reads `pals.md` + `data/pals.json`, emits one breeding-path URL.
- `build_site.py` — generates `index.html`: every Pal linked to its breeding path from the
  Pals owned. Imports `build_url` / `load_owned` / `load_pals` from `breeding_path.py`.
- `index.html` — generated, committed, and served by GitHub Pages. Do not hand-edit.

## Usage

```sh
python3 breeding_path.py Anubis           # print one URL
python3 breeding_path.py Anubis --open    # and open it in a browser
python3 build_site.py                     # regenerate index.html after editing pals.md
python3 refresh_pals.py                   # after a Palworld update adds Pals
```

After checking a Pal off in `pals.md`, rerun `build_site.py` and commit the regenerated
`index.html` — the owned list is baked into all 297 links, so every link changes.

## GitHub Pages

Published from the repo root of the default branch: https://nielsutrecht.github.io/palworld/
The repo is public because Pages on a private repo needs a paid plan. `index.html` is fully
static and self-contained (no external assets), so it also works opened straight from disk.

Target matching is case-insensitive and suggests near misses on a typo. Both scripts are
stdlib-only — no dependencies, no venv.

## Conventions

- `pals.md` is sorted by display name so diffs stay readable as Pals get checked off. A
  checked name that isn't in `data/pals.json` is a hard error, not a silent skip.
- Both scripts write progress to stderr and only the URL to stdout, so the URL pipes cleanly.
