# Palworld breeding paths

**→ [nielsutrecht.github.io/palworld](https://nielsutrecht.github.io/palworld/)**

I keep a markdown file of which Pals I own. This turns it into a page where every Pal in
the game links to its shortest breeding path *from the Pals I actually have* — so instead
of "Anubis needs Anubis parents", I get a chain I can actually run:

> Anubis is 2 breeds away
> 1. Jormuntide + Blazamut = Dualith
> 2. Dualith + Blazamut = Anubis

The breeding maths is done by [palworld.gg](https://palworld.gg/breeding-path), which
takes the target Pal and the Pals you own as URL parameters. All this repo does is keep
that URL in sync with a list I edit by hand — for all 297 breedable Pals at once.

## Using it

Everything is driven by [`pals.md`](pals.md), the only file edited by hand:

```markdown
# Wanted

- Ophydia
- Pyrin

# Pals I own

- [x] Amione
- [ ] Anubis
- [x] Arsox
```

`# Wanted` is a wishlist, in priority order — it gets its own section at the top of the
page. `# Pals I own` is the full roster; tick a Pal when you catch or breed it.

Then rebuild the page and commit:

```sh
python3 build_site.py
```

The list of Pals you own is baked into all 297 links, so **every link changes whenever you
gain a Pal** — `index.html` has to be regenerated and committed alongside any `pals.md`
edit, or the published page will quietly serve stale breeding paths.

## Scripts

| | |
| --- | --- |
| `build_site.py` | Regenerates `index.html`. Run after every `pals.md` edit. |
| `breeding_path.py <Pal>` | Prints the breeding-path URL for a single Pal. `--open` opens it. |
| `refresh_pals.py` | Regenerates `data/pals.json` from palworld.gg. Only needed when a Palworld update adds Pals. |

Python 3.10+, standard library only — no dependencies, no venv.

An unknown Pal name in `pals.md` is a hard error naming the line and suggesting a fix,
rather than being skipped:

```
$ python3 build_site.py
these wanted Pals are not in data/pals.json (typo, or the Pal is not breedable):
  pals.md:3: Ophidia (did you mean: Ophydia, Elphidran?)
```

That is deliberate. A silently dropped name would still produce a perfectly plausible
page — just with longer breeding paths than necessary, and no way to notice.

## How it works

palworld.gg's URL takes **internal Pal ids**, not display names and not its own url slugs.
The three genuinely differ — Lamball is `sheepball`, Amione is `clionetwins` — and a few
ids happen to match the slug (`anubis` really is `anubis`), which makes the parameter look
slug-shaped when it isn't. So names in `pals.md` are resolved through `data/pals.json`, a
generated id↔name map.

That map is extracted from palworld.gg's own bundled Pal data by `refresh_pals.py`. It
lives in a content-hashed JavaScript chunk whose URL changes every time the site is
rebuilt, so the script rediscovers it from the page each run instead of hardcoding a URL
that would rot.

---

Not affiliated with palworld.gg or Pocketpair. Just a static page of links.
