# Datalog Query Cookbook

Queries for `logseq.DB.datascriptQuery`. Each has the query, return shape, and description.

## Table of contents

- Namespace-stripped keys
- Counts
- Tags / refs
- Graph health
- Time windows
- Namespaces
- Properties
- Advanced
- Gotchas

## Namespace-stripped keys

`datascript_query` results pass through `normalize-keyword-for-json` with `camel-case? false` (see `sdk/utils.cljs:6` and `api.cljs:882`), so pull results return kebab-case keys: `block/uuid`, `block/created-at`, `block/path-refs`, `db/id`. Methods like `get_page`/`get_block` use `camel-case? true` and return camelCase (`uuid`, `createdAt`, `pathRefs`).

Defensive reader (Python):

```python
def block_uuid(p):     return p.get("uuid") or p.get("block/uuid")
def block_page_id(p):  return (p.get("page") or {}).get("id") or (p.get("page") or {}).get("db/id")
def block_created(p):  return p.get("createdAt") or p.get("block/created-at")
```

## Counts

```clojure
;; Total blocks → scalar int
[:find (count ?b) . :where [?b :block/uuid _]]

;; Total pages → scalar int
[:find (count ?p) . :where [?p :block/name _]]

;; Journal pages → scalar int
[:find (count ?p) . :where [?p :block/journal-day _]]
```

The `. :where` (single-value aggregate) returns a scalar; without the `.` you get `[[n]]`.

## Tags / refs

```clojure
;; Distinct referenced page names
[:find [?name ...]
 :where [?b :block/refs ?p] [?p :block/name ?name]]

;; Tag frequency → [["name" 42] ...]
[:find ?name (count ?b)
 :where [?b :block/refs ?p] [?p :block/name ?name]]

;; Blocks tagged with a specific page (name is lowercased + sanitized)
[:find (pull ?b [*])
 :in $ ?target
 :where [?p :block/name ?target] [?b :block/refs ?p]]
;; inputs = ["\"my-page\""]

;; Tags on a specific block
[:find [?name ...]
 :in $ ?uuid
 :where [?b :block/uuid ?uuid] [?b :block/refs ?p] [?p :block/name ?name]]
```

## Graph health

```clojure
;; Orphans — defined pages with no inbound refs and no blocks
[:find [?name ...]
 :where
 [?p :block/name ?name]
 (not [?b :block/refs ?p])
 (not [?child :block/page ?p])]

;; Broken refs — referenced but never created (no file, not journal, no blocks)
[:find [?name ...]
 :where
 [_ :block/refs ?p]
 [?p :block/name ?name]
 (not [?p :block/file _])
 (not [?p :block/journal-day _])
 (not [?child :block/page ?p])]

;; Pages with no outbound refs
[:find [?name ...]
 :where
 [?p :block/name ?name]
 (not-join [?p]
   [?b :block/page ?p]
   [?b :block/refs _])]
```

## Time windows

`:block/created-at` and `:block/updated-at` are epoch millis.

```clojure
;; Blocks created in [from, to]
[:find (pull ?b [:block/uuid :block/content :block/created-at :block/page])
 :in $ ?from ?to
 :where
 [?b :block/created-at ?ts]
 [(>= ?ts ?from)] [(<= ?ts ?to)]]
;; inputs = [from_ms, to_ms]

;; Journal pages in a date range — journal-day is YYYYMMDD int
[:find [(pull ?p [*]) ...]
 :in $ ?from ?to
 :where
 [?p :block/journal-day ?d]
 [(>= ?d ?from)] [(<= ?d ?to)]]
;; inputs = [20260101, 20260417]

;; Blocks on a specific journal day via parent page
[:find [(pull ?b [*]) ...]
 :in $ ?day
 :where
 [?p :block/journal-day ?day] [?b :block/page ?p]]
```

## Namespaces

```clojure
;; Pages under a prefix
[:find [?name ...]
 :in $ ?prefix
 :where
 [?p :block/name ?name]
 [(clojure.string/starts-with? ?name ?prefix)]]
;; inputs = ["\"notes/\""]

;; Direct children at a given depth
[:find [?name ...]
 :in $ ?prefix ?depth
 :where
 [?p :block/name ?name]
 [(clojure.string/starts-with? ?name ?prefix)]
 [(clojure.string/split ?name "/") ?parts]
 [(count ?parts) ?n]
 [(= ?n ?depth)]]
```

For simple cases prefer `get_pages_from_namespace(ns)` — returns sorted PageEntity[].

## Properties

```clojure
;; All property keys in use (distinct)
[:find [?k ...]
 :where
 [?b :block/properties ?props]
 [(keys ?props) ?ks]
 [(identity ?ks) [?k ...]]]

;; Blocks with a specific property
[:find [(pull ?b [*]) ...]
 :in $ ?key
 :where
 [?b :block/properties ?props]
 [(get ?props ?key) ?v]
 [(some? ?v)]]
;; inputs = [":status"]

;; Blocks with property = value
[:find [(pull ?b [*]) ...]
 :in $ ?key ?val
 :where
 [?b :block/properties ?props]
 [(get ?props ?key) ?v]
 [(= ?v ?val)]]
;; inputs = [":status", "\"draft\""]
```

## Advanced

```clojure
;; Largest pages by block count (sort + slice client-side)
[:find ?name (count ?b)
 :where
 [?p :block/name ?name]
 [?b :block/page ?p]]

;; TODO blocks (marker is :block/marker; also DOING DONE LATER NOW WAITING CANCELED)
[:find [(pull ?b [:block/uuid :block/content :block/marker :block/page]) ...]
 :where [?b :block/marker "TODO"]]

;; Blocks referencing a specific block by UUID (i.e. ((uuid)) refs)
[:find [(pull ?src [*]) ...]
 :in $ ?target-uuid
 :where [?t :block/uuid ?target-uuid] [?src :block/refs ?t]]

;; Resolve ((uuid)) targets cited inside a source block
[:find [(pull ?ref [*]) ...]
 :in $ ?src-uuid
 :where
 [?b :block/uuid ?src-uuid]
 [?b :block/refs ?ref]
 [?ref :block/uuid _]]
```

## Gotchas

- String inputs pass through `cljs.reader/read-string` (see `api.cljs:870-879`). Wrap strings in doubled-up quotes: `"\"my-page\""`. Numbers pass through as-is.
- `:block/name` is always lowercased + sanitized. Use `:block/original-name` for display case.
- `pull ?p [*]` is expensive on property-heavy pages — prefer explicit attribute lists.
- `datascript_query` calls `d/q` with `disable-reactive? true`, so it won't hit the reactive cache.
- For human-friendly shorthand queries, prefer `q(dslString)` — DSL grammar in `src/main/frontend/db/query_dsl.cljs`.
