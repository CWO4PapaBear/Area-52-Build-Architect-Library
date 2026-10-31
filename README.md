# Area-52-Build-Architect-Library
This library is intended to serve as a resource for sharing and storing Area 52 builds.

## Portable build tooling

Requires Python 3.10 or newer; no third-party Python dependencies. The repository's existing CC0 license is retained. Export only content you are entitled to contribute under CC0. The author alias is retained as metadata.

Copy a build using the existing in-game **Copy Build Code** button and save the code as UTF-8 text. Export it into a local checkout:

```powershell
python tools/library.py export my-build.txt --root . --author "Public alias" --catalog "your-reviewed-catalog-version" --accept-cc0
```

This writes a readable JSON revision under `builds/<global-uuid>/<revision>.json`. It does not upload anything. For an update, supply the original `--id` and a new `--revision`. Existing revisions cannot be overwritten with different content. Local server IDs, account ownership, Featured and certification flags are excluded.

Convert a record back to a code for the existing in-game import dialog:

```powershell
python tools/library.py import builds/<uuid>/1.json --catalog "your-reviewed-catalog-version" --output imported-build.txt
python tools/library.py validate --root .
python tools/library.py index --root . --output library-index.json
python -m unittest discover -s tests
```

Output files are not overwritten. Import requires a matching declared catalog version; the receiving server must still validate actual spell/enchant availability and eligibility. Importing never grants ownership, activates a build or assigns an archetype. Build spell IDs preserve the selected rank; `Level` records the learning level, not a talent rank number.

The JSON includes complete selections, enchant stacks, equipment preferences, comments and descriptions. `build_sha256` covers normalized build data. The generated index hashes complete record bytes. No game icons or other client assets are bundled.

## In-game integration

The intended controls are **Publish Build** (public GitHub library) and **Save Build** (existing realm-local behavior), with Save immediately to the right. Import retains local/code choices and adds **Update Library**, which refreshes shared builds into the existing server list. Browse individual builds in the generated GitHub `CATALOG.md` and copy a build page's code into the game. See [the integration contract](docs/game-integration.md) for tooltip wording, privacy, acknowledgement and worker requirements.

The portable tooling, durable server publication queue, GitHub publisher and validated read-cache components are implemented locally with offline tests. The worker requires explicit `--publish` to perform writes; its default mode only reports queue counts. Authentication remains server-side.

The Update Library handler, client menu, guarded realm importer, Save/Publish separation and authenticated publication outbox are prepared with offline native catalog, callback lifecycle and database rollback checks. The existing list is paged without the former 256-record query limit. The production worker is staged separately for authorized deployment; no service has been installed and no existing player builds are published automatically. Native-wire checks use the real core codec, while remote failures use adapters; these are not gameplay or live GitHub delivery tests.

Generate a readable catalog from local immutable records without publishing:

```powershell
python tools/catalog.py --root . --output .
```
