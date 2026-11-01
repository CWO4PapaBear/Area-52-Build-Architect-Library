# Area 52 Build Architect Library

Current Area 52 builds and portable build tools; prior revisions remain in Git history. Browse [the build catalog](CATALOG.md).

## Repository ownership

This repository owns `builds/`, `catalog/`, `index.json`, `CATALOG.md`, the portable build-code format, import/export tooling, and catalog rendering. Existing CC0 contribution terms and explicit author consent remain unchanged. Publishing a build does not grant Featured status, certification, or character ownership.

The realm publication worker, authenticated database outbox ingestion, native catalog validator, private notifications, cache/import integration and deployment instructions belong to [the server repository](https://github.com/CWO4PapaBear/azerothcore-wotlk-coa/tree/feature/area52-build-library-worker/apps/area52-build-library). That branch pins this repository as a dependency. Do not deploy a worker from an old revision of this Library branch.

## Portable tools

Python 3.10 or newer; no third-party dependencies. Commands below operate on local files and do not upload anything:

```sh
python tools/library.py export my-build.txt --root . --author "Public alias" --catalog "area52-v1" --accept-cc0
python tools/library.py import builds/BUILD-NAME--BUILD_UUID/current.json --catalog "area52-v1" --output imported-build.txt
python tools/library.py migrate --root .
python tools/library.py validate --root .
python tools/library.py index --root . --output library-index.json
python tools/catalog.py --root . --output .
python -m unittest discover -s tests
```

Export only content you are entitled to contribute under CC0. The code input is the in-game Copy Build Code output. Updates use the original `--id` with a new `--revision`; only the current revision remains in the working tree. A stale revision or different content with the same revision is rejected. Import validates the portable format, not live spell eligibility. The receiving server must check its current native catalog and rules.

Local server IDs, account ownership, Featured assignment and certification flags are not portable grants. The format retains selected spell/rank IDs, learning levels, enchant stacks, equipment preferences, comments and descriptions. No client assets, credentials, native binaries or realm database exports belong here.

## Current-version layout

Each stable public UUID has one `builds/<build-name>--<uuid>/current.json` and one `catalog/<build-name>--<uuid>/README.md`. The record retains its revision number, author, catalog compatibility and build hash. Index schema 2 contains one row per UUID. The build-code and record formats remain schema 1. Names are converted to bounded filesystem-safe slugs; UUID suffixes distinguish identical names and authors. Renaming a build moves its folder while preserving its identity.

`CATALOG.md` lists current names and public author aliases with links. Search that page in your browser, or search repository content on GitHub (subject to GitHub's branch indexing). The build pages and JSON records also retain both names. Git history preserves previous versions and paths; reducing the current tree does not shrink historical Git objects.

## Existing library migration

Run `python tools/library.py migrate --root .` in a clean reviewed checkout. It validates existing records and indexed hashes, selects the highest revision per UUID, renders the current pages, and removes superseded generated files. Edited catalog pages, conflicting records, unsafe paths and missing indexed records stop the migration before writes. Review and commit the resulting moves/deletions normally; never rewrite or force-push history. The command is idempotent after a completed migration. Local multi-file writes are not a transaction: if interrupted, preserve the worktree, inspect `git diff`, and restore only this operation's generated paths from the reviewed Git baseline before retrying.

Deploy the updated worker/importer with its pinned portable tools together with the schema-2 repository transition. Pause publication and resolve existing uncertain commit intents before changing paths on the serving branch. Old schema-1 workers cannot read schema 2. The new importer can read either; the new publisher refuses a nonempty legacy index until it is migrated. Feature-branch preparation does not deploy or restart the realm worker.

## Ownership

Public author aliases are display text, never update credentials. The authenticated server worker keeps a private binding of installation UUID, owner account and local build ID to a public UUID. Updates require that binding and a matching previously published record. Renames do not reset it, and another installation using the same author alias gets a different UUID. Keep the private queue and installation identity when deploying; never recreate bindings by matching author/name. These checks do not constrain someone with direct repository write credentials: independently administered servers must not share unrestricted write tokens. Their contributions need a trusted ingestion service or reviewed pull requests.
