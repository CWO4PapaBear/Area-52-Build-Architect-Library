# In-game shared library integration

Implementation contract; the native connection and publishing worker are not deployed.

## Buttons

Keep **Publish Build** in its current position. Add **Save Build** immediately to its right.

Save tooltip: “Save this build to this server's build library. It will not be uploaded to the public Shared Library.”

Publish tooltip: “Publish a copy of this build to the public Area 52 Shared Library on GitHub so players on other servers can view and import it.”

Save uses the existing realm save validation, ownership, revision and acknowledgement path. Its visibility remains the same as the current Publish action; local does not mean private or PC-only. Rename its confirmation, progress and result messages consistently. Preserve the existing Draft selector and button texture corrections.

Publish requires explicit confirmation showing public author alias, title, description and CC0 contribution terms. Do not publish account IDs, character GUIDs, local build IDs, ratings, certification flags, ownership or private drafts. Public descriptions must be reviewed by their author. Never automatically publish existing builds or later local edits.

## Import

Offer three choices under Import Build: **This Server**, **Import Build Code**, **Update Library**. No separate in-game Shared Library browser is planned. Update Library requests a server-wide refresh of new and updated public builds into the existing server build list. It does not change the open editor, personal copies, active builds or Featured archetype assignments. Shared revisions are separate ownerless records; edits require a personal copy. Never overwrite personal records or silently accept changes to a shared record made locally.

For one build, browse `CATALOG.md` on GitHub, open its readable build page, copy the fenced A52B1 code and use Import Build Code. Historical public revisions remain available. Copying or refreshing must not activate a build, learn spells, grant MEs, assign an archetype or mark anything Verified/Certified.

## Server boundary

The client has no GitHub credentials and makes no authenticated GitHub calls. A server-side adapter authenticates the player, validates catalog eligibility and serializes an immutable approved revision into a durable publication queue. Use a server-held installation identity and private local mapping for updates; a supplied public UUID alone never authorizes updating another author's build.

A worker publishes allowlisted build and index files with non-forced Git updates. Persist the intended commit and payload hash before updating the remote ref. After uncertain writes, reconcile immutable remote content; do not create duplicate revisions or blindly retry writes. Show queued, published, rejected or failed states distinctly. A successful local save is not a successful public publication. GitHub errors must never make Save Build unavailable.

Other servers fetch immutable, hash-checked library revisions into a local cache and import only new compatible revisions. Validate against the receiving server's actual catalogs, costs, rank rules and replacement requirements. A matching catalog label alone is insufficient native validation. Previously imported builds remain available when GitHub is unavailable. Disable publishing with a clear message when the worker is unavailable. Repository writes must not run on the world update thread.

Remote public builds are untrusted input. Enforce payload/count/text limits, reject unknown schema versions and malformed IDs, avoid Lua execution, neutralize UI links/control sequences in previews, and rate-limit authenticated submissions.

## Current implementation boundary

The CLI implements the portable format, existing A52B1 code conversion, immutable local revision storage, catalog-label checks and a hash-addressed index. `publication.py` now implements private SQLite queue persistence, owner/build identity separation, a saved-record confirmation boundary, non-forced GitHub publication and read-only recovery after uncertain writes. `cache.py` validates immutable record hashes and atomically stages a local public snapshot. `worker.py` leaves publication disabled unless explicitly requested with `--publish`.

These components have offline tests, including the actual core wire encoder. A separate staged native Update Library endpoint uses authenticated self-whispers, request tokens, asynchronous prepared statements and per-account throttling. The worker imports guarded shared records transactionally; isolated production-schema MySQL checks cover preservation, revisions, failure rollback and refresh retries. The staged client adds the simplified import menu and preserves the Featured dropdown correction. These changes are not installed.

The staged publication endpoint captures the authenticated owner's saved revision in a durable MySQL outbox, guarded against concurrent revision/ownership changes. The worker moves it idempotently into the private SQLite queue. Save/Publish UI separation is staged: Publish saves first, then confirms a public alias and CC0 terms against that saved revision. An uncertain retry requests status rather than submitting again. Neither source nor UI has been deployed.

Native catalog generation and handler lifecycle checks now pass offline. The receiving server's pinned native rules validate every progression level from 1 through 80 and enchant slot/stack limits at both import and publication. Queued records are checked again before a new remote write. Source or catalog drift stops processing for requalification. Player ownership and runtime spell-group eligibility remain authoritative when a player applies a build; publication is not certification.

The 256-record query limit is removed; the existing response paging remains in use. An isolated MySQL fixture covers more than 300 records and preserves personal and Featured builds. Public Draft copies become ordinary Leveling builds with local archetype assignments removed, including the catalog's copyable code; the original local build is unchanged.

The prepared worker uses a private repository-scoped token, a single-instance process lock, durable queues and a systemd service. Its installation and startup belong to the separately authorized activation package. `worker_service.py --config PATH --check` performs read-only catalog/credential checks; `--offline` omits remote access. The production service enables publication only after the package's post-readiness publication has completed. No remote publication or installed service is established by offline tests.

The publication and refresh tables must be migrated before starting a binary that registers their prepared statements, even with `CoA.BuildLibrary.Enable=false`. Feature disablement does not remove startup SQL registration dependencies. Workers are single-instance processes; service configuration must enforce that constraint. An accepted outbox row is not a published build: only the durable publisher's verified GitHub receipt permits the published state.

Keep the queue and its identity bindings in a private, access-controlled server directory outside Git. Back up the database and its WAL consistently; losing the bindings can fork public identities. Run one publishing worker per queue. Only the authenticated server adapter may call enqueue; do not expose the Python enqueue API directly to clients. Use a dedicated repository-scoped credential held by the worker. Never configure this with a token supplied by a player or embed credentials in the client. Participating server administrators must be explicitly authorized; this does not create anonymous repository write access.

An uncertain result is retained for reconciliation. A confirmed matching descendant may be accepted; a changed index or record requires review. The current implementation intentionally does not silently rebase an uncertain publication or automatically repeat a branch update. A cached import is still subject to native catalog/rank validation; compatibility labels alone are not sufficient.
