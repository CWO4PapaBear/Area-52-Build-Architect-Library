# Area 52 Build Architect Library

Public, immutable Area 52 build revisions and portable build tools. Browse [the build catalog](CATALOG.md).

## Repository ownership

This repository owns `builds/`, `catalog/`, `index.json`, `CATALOG.md`, the portable build-code format, import/export tooling, and catalog rendering. Existing CC0 contribution terms and explicit author consent remain unchanged. Publishing a build does not grant Featured status, certification, or character ownership.

The realm publication worker, authenticated database outbox ingestion, native catalog validator, private notifications, cache/import integration and deployment instructions belong to [the server repository](https://github.com/CWO4PapaBear/azerothcore-wotlk-coa/tree/feature/area52-build-library-worker/apps/area52-build-library). That branch pins this repository as a dependency. Do not deploy a worker from an old revision of this Library branch.

## Portable tools

Python 3.10 or newer; no third-party dependencies. Commands below operate on local files and do not upload anything:

```sh
python tools/library.py export my-build.txt --root . --author "Public alias" --catalog "area52-v1" --accept-cc0
python tools/library.py import builds/BUILD_UUID/1.json --catalog "area52-v1" --output imported-build.txt
python tools/library.py validate --root .
python tools/library.py index --root . --output library-index.json
python tools/catalog.py --root . --output .
python -m unittest discover -s tests
```

Export only content you are entitled to contribute under CC0. The code input is the in-game Copy Build Code output. Updates use the original `--id` with a new `--revision`; existing revisions cannot be overwritten with different content. Import validates the portable format, not live spell eligibility. The receiving server must check its current native catalog and rules.

Local server IDs, account ownership, Featured assignment and certification flags are not portable grants. The format retains selected spell/rank IDs, learning levels, enchant stacks, equipment preferences, comments and descriptions. No client assets, credentials, native binaries or realm database exports belong here.
