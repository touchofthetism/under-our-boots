# Source library — `sources_library.json`

The shared evidence base for **Under Our Boots**: every web source cited by
any of the 404 installations in `installations.csv`, in one file that both
Claude (research) and Muse (verification + production) cite from.

## What's in it

- Built 2026-11-15 by parsing every `http(s)` URL out of the `sources`
  column of `installations.csv` and deduplicating: **856 unique sources**
  across 404 installations (15 sources support more than one installation;
  the widest supports 7).
- Format: **CSL-JSON** — one item per source with `id`, `type: webpage`,
  `title`, `URL`, `accessed`, and `collection` (the installation names that
  source supports).
- Titles are the URL's domain + path, taken from the URL itself. Pages were
  deliberately **not** fetched to harvest titles, so no title in this file
  is invented or paraphrased. When a source gets used in an episode, its
  real title is filled in at verification time.
- Archived copies: many URLs are already Wayback Machine snapshots (the
  dataset cites the archived version where the live page moved or died);
  `source_snapshots.csv` tracks snapshot coverage for the rest.

## Importing into Zotero (one step)

In Zotero: **File → Import…**, choose `sources_library.json`, and import
into a new collection. Every source lands as a webpage item, tagged by the
`collection` field to the installation(s) it supports, ready to cite from
scripts, cards, and production logs.

## The one thing Shefton must do to make this a live shared library

1. Create a **free Zotero account** (zotero.org) and, in Zotero's web
   library, create a **group library named "Under Our Boots"** and share it.
2. Generate a **Zotero API key** for that account and hand it to Muse
   **through the secure credential entry** (never in chat or email).

With that, Muse syncs this file into the group library via the API and
keeps it updated as the dataset grows — Claude and Muse then work from
the same live library instead of passing files around.

## Until then

**This file is the canonical source library.** Claude cites from it when
building story cards; Muse verifies against it when checking cards and
scripts. If a source isn't in this file, it isn't in the dataset — add it
to the installation's `sources` in the Drive research folder first, and it
will flow into the next build of this file.
