# front-map

> A **deterministic, agent-queryable design-system index** (tokens · primitives · routes · usage)
> — so UI generation is grounded in an index instead of code written blind.

**Status: v1** (changes: [`CHANGELOG`](./CHANGELOG.md)). A **standalone** CLI: no service, no network,
no daemon. It reads a project's `web/` directory and writes four JSONL indexes. It is built to be dropped
into any front-end repo an AI coding agent (or a UX review agent) works on, so the agent can query the
**real** design system before writing a view — instead of reinventing a button or hardcoding a colour.

## What this is *not*

- **Not a component library.** It ships no components, no CSS, no runtime. It only describes yours.
- **It does not generate UI.** Every verb is read-only except `build`, which writes only index files.
- **Not a design-token compiler.** It reads tokens where they already live; it does not emit them.
- **Not a general symbol index.** See [`code-map`](https://github.com/Avadis7860/code-map) for that.
- **Not a linter or an accessibility checker.** `check` reports index consistency and a few structural
  signals, never a quality verdict on your components.

## Why a separate tool from [`code-map`](https://github.com/Avadis7860/code-map)

`code-map` answers **"where is the code, who calls what"**: it extracts raw *symbols*
(`class/function/type/const`) and the import graph. To it, `Button` is just an anonymous `kind:function` —
it **does not model** design-system semantics. front-map answers **"which primitive, which token, which
route for X"**: it models exactly what code-map does not.

The boundary: front-map vendors the *public* `tree-sitter` engine (the same optional extra code-map uses)
plus a copy of the stdlib `core/` base; it **does not depend on code-map** at runtime and **does not
duplicate** its general symbol extractor. Its four extractors are narrow and design-system-semantic.

**Generic by convention (the way code-map is generic by language).** Where code-map varies by *language*
through *engines*, front-map varies by *convention* through **adapters**, along two orthogonal axes:

- **router**: `tanstack` (TanStack code-based `createRoute`) · `react-router` (JSX `<Route>`);
- **primitives**: `barrel` (`components/ui/index.ts` re-exports) · `dir-scan` (one `.tsx` per primitive, no
  barrel) · `astro` (one `.astro` per primitive, detail read from the frontmatter).

The convention is **auto-detected** (sniffing the router's imports, looking for a barrel) — or forced in
`.frontmap.toml`. An unknown axis degrades gracefully and says so; adding a convention means adding one
adapter to the registry (`src/frontmap/adapters/`) and nothing else moves.

## Verbs

| Verb | Purpose |
|---|---|
| `frontmap build [--root R]` | (re)build the 4 indexes, incremental by hash |
| `frontmap tokens [--group G]` | design tokens (optional filter: accent/status/surface/radius/…) |
| `frontmap primitives` | primitive catalogue (summary) |
| `frontmap primitive <name>` | detail of one primitive: props, variants, defaults |
| `frontmap routes` | route tree (path → component) |
| `frontmap where <intent>` | "which primitive, which token for X?" (bounded lexical ranking) |
| `frontmap usage <name>` | **inverted** index: "who consumes this primitive or token?" |
| `frontmap consumers <file>` | what one screen consumes: primitives + tokens + route |
| `frontmap detect` | conventions auto-detected in the repo (router / primitives) |
| `frontmap check` | consistency, freshness and signals (dynamic routes, primitives never consumed) |

## The four indexes

- **`tokens.jsonl`** — `{name, value, group, source_file, line}` read from CSS (`@theme` + `:root`).
  **Pure CSS, always available** (no dependency).
- **`primitives.jsonl`** — `{name, file, line, props, variants, defaults, lead}` from the resolved
  primitives adapter (barrel, dir-scan **or** astro). The **rich** catalogue needs `tree-sitter` (extra
  `[ts]`), and for the `astro` convention also the astro grammar (extra `[astro]`); the **names** — the
  pivot contract for `usage` — are extracted without either (regex plus filesystem). `frontmap check`
  carries a typed `primitives_status` (`verified` | `names_only` | `unavailable`), so it is never falsely
  green on a source it could not parse.
- **`routes.jsonl`** — `{var, path, full_path, component, parent, is_root, file, line}` from the resolved
  router adapter (tanstack **or** react-router). Requires `tree-sitter`.
- **`usage.jsonl`** — `{consumer, kind, primitives, tokens, route}`: the **inverse** consumption index
  (who imports which primitive, which literal tokens, under which route). **Pure Python** — it works
  without `tree-sitter` (only the `route` link degrades to `null`).

## Principles

- **Stdlib-pure core** (CSS tokens): installs anywhere, offline. **TSX** support (via `tree-sitter`,
  pre-built wheels) is an **optional extra**; when absent, primitives and routes come back empty and
  `check` says so — it never errors out.
- **`build` writes, queries read**: `frontmap build` materialises the indexes; every other verb only
  reads. No heavy work hides inside a query.
- **Freshness by content hash, never mtime**: the index is incremental and idempotent — unchanged sources
  are skipped. Deterministic across operating systems (newlines normalised).
- **A stale catalogue is never served silently**: every read verb emits a staleness signal on **stderr**
  (`∅` never indexed · `≠` modified since the build · `–` gone from disk) without touching the JSON on
  stdout, which is a contract for downstream consumers. An honest empty answer beats a wrong one: the
  false positive is what costs, because it removes the doubt.
- **Generic by convention**: sources and both axes (router / primitives) are declared in a
  [`.frontmap.toml`](./.frontmap.toml) at the root of the target repo, with the convention auto-detected by
  default. Proven on three real projects with opposite conventions: a dashboard (TanStack + barrel), an
  aggregator (react-router + dir-scan) and a marketing site (Astro).

## Install

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'          # dev includes tree-sitter (primitives + routes)
frontmap build --root /path/to/a/front-end/repo
frontmap primitive Button --root /path/to/a/front-end/repo
```

## Licence

**Apache-2.0** — see [`LICENSE`](./LICENSE) and [`NOTICE`](./NOTICE).

Installation, use, modification and redistribution are granted, including for commercial use. Section 6
grants no rights over the **name**; the patent clause (section 3) grants the patents needed to use the
work and terminates automatically for anyone who sues the project for patent infringement.
