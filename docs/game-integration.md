# Build Architect integration boundary

The Library repository stores shared build content and portable codecs. The [server worker](https://github.com/CWO4PapaBear/azerothcore-wotlk-coa/tree/feature/area52-build-library-worker/apps/area52-build-library) owns database access, native validation, publication credentials, safe retries and private in-game notifications.

Save Build retains realm-local behavior. Publish Build saves the exact revision and requests explicit public author/CC0 consent before creating an authenticated outbox request. A timeout is not permission to create another request. The server retains its private request-to-public-ID binding and commit intent, checks remote readback, and only then reports publication complete.

The server imports the portable codec and catalog renderer from a pinned Library commit. Update that pin deliberately, run both tool and worker tests, and qualify the native validator against the deployed rules. A repository relocation does not install a service or change current gameplay.
