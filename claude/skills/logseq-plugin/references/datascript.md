# Datascript Queries

`logseq.DB.datascriptQuery(q)` runs Datalog against the user's graph. Two footguns that eat hours when unknown.

## 1. Namespace-stripped pull keys

A pull like `:block/uuid` comes back on the result object as `pull.uuid`, **not** `pull["block/uuid"]`. Nested pulls flatten too: `:block/page` with a nested `:db/id` becomes `pull.page.id`, not `pull["block/page"]["db/id"]`.

DB-based graphs sometimes use `:block/title` instead of `:block/content`. Always fall back to both.

**Defensive reader:**

```ts
function normalizeHit(row: any) {
  const pull = Array.isArray(row) ? row[0] : row;
  if (!pull) return null;

  const uuid = pull.uuid ?? pull["block/uuid"];
  const content = pull.content ?? pull.title
                ?? pull["block/content"] ?? pull["block/title"]
                ?? "";
  const pageRaw = pull.page ?? pull["block/page"];
  const pageId = pageRaw?.id ?? pageRaw?.["db/id"];
  const createdAt = pull["created-at"] ?? pull.createdAt ?? pull["block/created-at"];

  if (!uuid || !content || pageId == null) return null;

  return {
    uuid,
    content,
    page: {
      id: pageId,
      name: pageRaw.name ?? pageRaw["block/name"] ?? "",
      originalName: pageRaw["original-name"] ?? pageRaw.originalName ?? pageRaw["block/original-name"],
      journalDay: pageRaw["journal-day"] ?? pageRaw.journalDay ?? pageRaw["block/journal-day"],
    },
    createdAt: createdAt ?? 0,
  };
}
```

## 2. `diagnoseSchema` at startup

Before writing any real query, log a sample so you can see the actual shape your user's graph returns:

```ts
async function diagnoseSchema(): Promise<void> {
  try {
    const sample = await logseq.DB.datascriptQuery(
      `[:find (pull ?b [*]) . :where [?b :block/uuid _] [?b :block/page _]]`,
    );
    console.log("[my-plugin] sample block:", sample);

    const createdCount = await logseq.DB.datascriptQuery(
      `[:find (count ?b) . :where [?b :block/created-at _]]`,
    );
    const journalDayCount = await logseq.DB.datascriptQuery(
      `[:find (count ?p) . :where [?p :block/journal-day _]]`,
    );
    console.log("[my-plugin] counts:", { createdCount, journalDayCount });
  } catch (e) {
    console.error("[my-plugin] diagnose failed:", e);
  }
}
```

Run this once at startup (behind a one-shot flag so it doesn't spam). When a user reports "nothing works," the output tells you immediately whether `:block/created-at` is populated or not.

## 3. Common query shapes

**Blocks created in a time window:**

```clojure
[:find (pull ?b [:block/uuid :block/content :block/title :block/created-at
                 {:block/page [:db/id :block/name :block/original-name :block/journal-day]}])
 :where
  [?b :block/created-at ?ts]
  [(>= ?ts ${fromMs})]
  [(<= ?ts ${toMs})]
  [?b :block/page ?p]]
```

**Blocks on journal pages in a journal-day window** (fallback when `:block/created-at` is empty — file graphs without timestamps):

```clojure
[:find (pull ?b [:block/uuid :block/content :block/title :block/created-at
                 {:block/page [:db/id :block/name :block/original-name :block/journal-day]}])
 :where
  [?b :block/page ?p]
  [?p :block/journal-day ?day]
  [(>= ?day ${fromJd})]
  [(<= ?day ${toJd})]]
```

`journal-day` is an integer like `20260417` (YYYYMMDD). Convert via:

```ts
const jd = d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();
```

**Pages with a given tag:**

```clojure
[:find (pull ?p [*])
 :where
  [?p :block/tags ?t]
  [?t :block/name "${tag}"]]
```

**Backlinks to a page:**

```clojure
[:find (pull ?b [*])
 :where
  [?b :block/refs ?r]
  [?r :block/name "${pageName}"]]
```

## 4. DB-graph vs file-graph

- **DB-graph** (Logseq DB-based, master branch): `:block/created-at` is always populated and reliable. Primary query works.
- **File-graph** (Logseq stable 0.10.x, plain `.md` files): `:block/created-at` may be `0` or missing for blocks whose files don't have reliable filesystem mtime (e.g. cross-machine sync, git-based workflow). Fall back to `queryBlocksByJournalDay` — it relies on the page's journal-day, which is always set for journal pages.

Ship both queries and fall back automatically. The diagnostic output makes it obvious which mode the user is in.

## 5. Watching for changes

`logseq.DB.onChanged(cb)` fires on any DB mutation. Debounce — Logseq batches rapid mutations:

```ts
const debouncedRerender = debounce(rerender, 500);
logseq.DB.onChanged(debouncedRerender);
```

Don't call `datascriptQuery` from inside `onChanged` without a debounce — you'll re-query for every character the user types.
