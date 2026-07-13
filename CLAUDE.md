# Palworld breeding helper

Generates a [palworld.gg breeding-path](https://palworld.gg/breeding-path) link from a
markdown file that tracks which Pals I own, so the site can compute the shortest breeding
chain to a target Pal.

See [README.md](README.md) for what the project is and how to run it. This file covers the
things that are easy to get wrong and expensive to rediscover.

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

- `pals.md` — the tracking file, and **the only file you edit by hand**. Two sections:
  - `# Wanted` — a hand-ordered wishlist of plain bullets (`- Ophydia`). Order is
    preserved in the output; it reads as a priority list. Rendered as its own section at
    the top of the page. A wanted Pal that is also owned stays in the section and is
    tagged `owned` like anywhere else.
  - `# Pals I own` — one checkbox per breedable Pal; ticked = owned.

  The two shapes are parsed separately and are section-scoped, so a plain bullet can never
  be read as owned and a checkbox can never be read as wanted. A name in either section
  that isn't in `data/pals.json` is a hard error with its line number and a suggestion —
  never a silent skip, since a dropped name would quietly lengthen every breeding path.
- `data/pals.json` — generated `{id, name, slug}` map. Do not hand-edit.
- `refresh_pals.py` — regenerates `data/pals.json` from the site.
- `breeding_path.py` — parses `pals.md`, resolves names to ids, builds URLs. Owns
  `parse_md` / `load_owned` / `load_wanted` / `build_url`; also the single-Pal CLI.
- `build_site.py` — generates `index.html` from those helpers. Import them rather than
  re-parsing `pals.md` or re-encoding URLs; the comma encoding in particular is load-bearing
  (the site's own links keep commas literal, so `urlencode` is called with `safe=","`).
  `--out DIR` writes elsewhere; CI uses it to build into `_site`.
- `index.html` — generated, gitignored, built by CI. Run `build_site.py` to preview locally.

## GitHub Pages

https://nielsutrecht.github.io/palworld/ — built and deployed by
`.github/workflows/pages.yml` on every push to `main`. The Pages source is **GitHub
Actions**, not a branch. The repo is public because Pages on a private repo needs a paid
plan.

`index.html` is generated and **deliberately not committed** (it is in `.gitignore`). CI
runs `build_site.py --out _site` and deploys that. Editing `pals.md` is therefore the only
step.

This replaced a committed-`index.html` setup that silently served stale breeding paths
whenever `pals.md` was edited without rerunning `build_site.py` — which happened three
times in the first day. Do not reintroduce a committed `index.html`: a checked-in copy that
nothing serves is exactly the trap that caused it.

## Conventions

- `pals.md`'s owned section is sorted by display name so diffs stay readable as Pals get
  ticked off. The wanted section is *not* sorted — its order is the user's priority order
  and must be preserved.
- Scripts are stdlib-only. Keep it that way; there is no venv and no requirements file.
- Scripts write progress to stderr and only the URL to stdout, so the URL pipes cleanly.
- Never rewrite `pals.md` from a script — it is the user's hand-maintained input. Only
  `data/pals.json` and `index.html` are generated.

## Verifying a change

`index.html` is a pile of links whose correctness is not visible by inspection, so check
the actual output rather than trusting the build:

- `python3 build_site.py` prints the owned/wanted counts — they should match
  `grep -c '^- \[x\]' pals.md` and the wanted bullets.
- Render it: `python3 -m http.server` and open it. `file://` URLs are blocked in
  `playwright-cli`, so serve it over HTTP.
- Click a link through to palworld.gg and confirm a `BREEDING PLAN` actually appears; a
  malformed `own` list still renders a plausible-looking page, just a worse one.
