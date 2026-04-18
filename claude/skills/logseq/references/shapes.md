# Response Shapes

JSON shapes returned by Logseq's HTTP API. Top-level fields are camelCased by `sdk-utils/normalize-keyword-for-json` (see `src/main/logseq/sdk/utils.cljs:6`). Datalog pull results stay kebab-case (normalizer runs with `camel-case? false` for `datascript_query` — see `api.cljs:882`).

## Table of contents

- BlockEntity / PageEntity
- Linked references, search, configs
- Current graph, templates
- Datalog pull results (kebab-case)
- Error body

## BlockEntity

Returned by `get_block`, `get_current_block`, `insert_block`, `get_*_sibling_block`, `get_selected_blocks`, and as elements of `get_page_blocks_tree`.

```json
{
  "id": 13217,
  "uuid": "69e30997-c335-4977-a97b-f9a62114888e",
  "content": "- block markdown, including refs like [[Page]] and ((uuid))",
  "format": "markdown",
  "level": 1,
  "parent": {"id": 25},
  "left": {"id": 13216},
  "page": {"id": 25},
  "pathRefs": [{"id": 25}, {"id": 42}],
  "refs": [{"id": 42}],
  "properties": {"type": "note", "status": "draft"},
  "propertiesOrder": ["type", "status"],
  "marker": "TODO",
  "priority": "A",
  "createdAt": 1711920000000,
  "updatedAt": 1712001000000,
  "children": []
}
```

Notes:
- `children` only present when `includeChildren: true` is passed to `get_block`, or implicitly on `get_page_blocks_tree`.
- `left` is the sibling predecessor (outliner ordering). Root blocks have `left == parent`.
- `marker` only appears when the block starts with a TODO/DOING/DONE keyword.
- `id` is the datascript `:db/id` — unstable, do not persist. Use `uuid`.

## PageEntity

Returned by `get_page`, `get_current_page`, `create_page`, elements of `get_all_pages`, `get_pages_from_namespace`.

```json
{
  "id": 25,
  "uuid": "a1b2c3d4-...",
  "name": "apr 17th, 2026",
  "originalName": "Apr 17th, 2026",
  "journal?": true,
  "journalDay": 20260417,
  "format": "markdown",
  "file": {"id": 1892},
  "namespace": null,
  "properties": {"title": "Apr 17th, 2026"},
  "createdAt": 1712001000000,
  "updatedAt": 1712001000000
}
```

Notes:
- `name` is always lowercased + sanitized. Use `originalName` for display.
- `journalDay` is a YYYYMMDD integer; only present on journal pages.
- `journal?` field key survives normalization with the `?` — camelCased but question mark preserved (see `csk/->camelCase` behavior).
- Non-journal pages omit `journalDay` and `journal?`.
- Namespaced pages (`foo/bar`) have `namespace: {id}` pointing at the parent page.

## get_page_linked_references result

Returned by `get_page_linked_references(name)`. Shape is an array of `[PageEntity, BlockEntity[]]` tuples — each tuple groups all blocks on a given referencing page that point at the queried page.

```json
[
  [
    {"id": 500, "originalName": "Jan 3rd, 2026", "journalDay": 20260103, ...},
    [
      {"uuid": "...", "content": "Mentioned [[target]] in passing", ...},
      {"uuid": "...", "content": "Another block on this same page", ...}
    ]
  ],
  [
    {"id": 612, "originalName": "Reading List", ...},
    [{"uuid": "...", "content": "Added via [[target]]", ...}]
  ]
]
```

Empty when no references exist; returns `null` if the target page doesn't exist.

## search result

Returned by `search(q)`. Shape comes from `frontend.handler.search/search` which returns an indexed map. Confirmed against 0.10.15:

```json
{
  "blocks": [
    {
      "block/uuid": "...",
      "block/content": "... $pfts_2lqh>matched<pfts_2lqh$ text ...",
      "block/page": 25
    }
  ],
  "pages": ["apr 17th, 2026", "reading list"],
  "pages-content": [
    {"block/uuid": null, "block/snippet": "... $pfts_2lqh>match<pfts_2lqh$ ..."}
  ],
  "files": ["pages/apr_17th_2026.md"],
  "has-more?": false
}
```

- PFTS markers `$pfts_2lqh>...<pfts_2lqh$` wrap matched terms in snippets. Strip with `re.sub(r"\$pfts_2lqh>|<pfts_2lqh\$", "", s)` or use `strip_pfts` from `_logseq_common`.
- Keys here are kebab-case because this return hits `bean/->js` without normalization (see `api.cljs:1000`).

## user configs

Returned by `get_user_configs()`. Probed result on 0.10.15:

```json
{
  "preferredLanguage": "en",
  "preferredThemeMode": "dark",
  "preferredFormat": "markdown",
  "preferredWorkflow": "now",
  "preferredTodo": "TODO",
  "preferredDateFormat": "MMM do, yyyy",
  "preferredStartOfWeek": "6",
  "currentGraph": "logseq_local_/Users/you/notes",
  "showBrackets": true,
  "enabledJournals": true,
  "enabledFlashcards": true,
  "me": {
    "name": "user",
    "email": null,
    "avatar": null,
    "repos": [{"url": "logseq_local_/Users/you/notes"}]
  }
}
```

- `preferredDateFormat` uses Luxon tokens; matches what journal titles render as.
- `currentGraph` is the repo URL; strip the `logseq_local_` prefix to get a filesystem path.

## current graph

Returned by `get_current_graph()`. Returns `null` when on the local demo graph.

```json
{
  "url": "logseq_local_/Users/you/Documents/logseq-notes",
  "name": "logseq-notes",
  "path": "/Users/you/Documents/logseq-notes"
}
```

## templates

`get_current_graph_templates()` → `{templateName: BlockEntity, ...}`. `get_template(name)` → BlockEntity or null. `exist_template(name)` → bool.

## Datalog pull results (kebab-case)

`datascript_query` skips camelCase conversion (see `api.cljs:882`, `normalize-keyword-for-json` called with `false`), so raw pull results come back like:

```json
{
  "db/id": 13217,
  "block/uuid": "69e30997-...",
  "block/content": "...",
  "block/created-at": 1711920000000,
  "block/page": {"db/id": 25},
  "block/path-refs": [{"db/id": 42}]
}
```

Use the defensive reader (see `datalog.md` → "Defensive reader pattern") to support both shapes, since some nested lookups still collapse to the camelCased form.

## Error body

HTTP 200 with `{"error": "..."}` means the method threw. Common errors:

```json
{"error": "MethodNotExist: list_files_of_current_graph"}
{"error": "abc-123 is not a valid UUID string."}
{"error": "Custom block UUID already exists (69e...)."}
{"error": "Page title or block UUID shouldn't be empty."}
```

`classify_error` in `_logseq_common.py` maps these to `.kind` in `{"refused", "auth", "method", "args", "other"}`.
