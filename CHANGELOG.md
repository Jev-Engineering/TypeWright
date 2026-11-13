# Changelog

## Unreleased: rename to Typewright

- Refreshed `MANIFEST.sha256` (#108): the 29 `src/s1compiler/` entries now name their renamed
  `src/typewright/` files, and the 30 other stale hashes were recomputed, so
  `sha256sum -c MANIFEST.sha256` passes again. The listed file set is otherwise unchanged and
  `MANIFEST.sha256.as-shipped` is untouched. A regression test now fails if any listed file is
  missing or its hash is stale. Checksums are not signatures.
- AI Gateway example routes now require the exact pinned HTTPS URL for each route
  (approved endpoint policy). A worker whose `.env.local` points routes 3-5 at any
  other host, port or path now fails at startup, before any credential is sent.
  Redirects are refused and errors never echo the configured URL (#88).
- Documented which Python dependencies are exact pins and which float (bounded ranges, unpinned
  transitive packages, fresh CI resolution, no current resolved Python lock) in
  `docs/INTEGRATIONS.md`, linked from the README. The section also names the two tracked lock-like
  files and their scope: the npm lock for the Node gateway smoke (`ai` pinned at `7.0.114`) and the
  stale, Windows/CPython 3.13-only historical freeze in `reports/`. Regression tests check the
  tables against `pyproject.toml` and require every lock-like file in the tree to be named (#50).
  No lock was generated.
- CI hardening (#50): the `push` trigger is limited to `main` (pull requests still run), superseded
  pull request runs are cancelled by a per-PR concurrency group (runs on `main` each get their own
  group, so none is queued or cancelled), each job has a 20 minute timeout, `actions/checkout` and
  `actions/setup-python` are pinned to verified commit SHAs, pip installs retry up to three times
  through `scripts/ci_pip_install.sh` before failing, and the core matrix adds Python 3.14.
- Frozen hierarchy artifacts are now checked for lexical scope on load: node origins must match
  their export chain, references, `after` edges, and finals may not cross subgraph scopes (except
  through the inputs an export passes down), and exports must have descendant nodes (#85).
- Renamed the distribution and import package from `systemone-compiler` /
  `s1compiler` to `typewright`. The primary commands are `typewright` and
  `typewright-study`; `s1` and `s1-study` remain as deprecated aliases. The old
  `s1compiler` import path is removed.
- Unchanged by design: the `.s1.json` artifact extension, `systemone-*` format
  identifiers, the artifact provenance key, and the `S1_TEACHER_*` environment
  variables, so existing frozen artifacts and checksums stay valid.
- Historical verification reports, `reports/`, and the shipped manifests still
  record the old name because they describe what was run at the time.

## Unreleased: hierarchy v1

- Added a separate versioned hierarchy source and frozen graph artifact with
  validated typed references, conditional routes, nested reuse, and serial
  native leaf execution under one caller budget. Flat v1 remains supported.
- Added bounded DSPy structure and GEPA wording selection, four-split
  calibration/freeze flow, graph metrics, and durable attempt evidence for
  strict replay and resume.
- Added hierarchy CLI/schema/playground dispatch, packaged starter data, and
  synthetic support, PR-risk, and nested-reuse examples.
- Added a preregistered three-arm study runner and offline synthetic smoke.
  Its live protocol requires independent reviewed data and separate paid and
  teacher-sharing approvals; no measured hierarchy gain is claimed.
- Added `s1-study manifest` and `s1-study review`: a complete pre-spend live
  manifest with every run parameter, a digest-bound human review of required
  attestations, and a live `select --reviewed-manifest` gate that refuses any
  parameter drift before building a provider or teacher. No live study has
  been registered, reviewed, or executed.
- Rebuilt the tracked `wheels/` wheel from current main so it includes the hierarchy modules and
  the `s1-study` entry point, and refreshed the hashes in `MANIFEST.sha256` for files changed since
  it was last updated. `MANIFEST.sha256.as-shipped` is unchanged. Release wheels remain unsigned
  local builds, and the manifest is an integrity check, not a signature.

See [migration](docs/HIERARCHY_MIGRATION.md) for format and caller changes.
