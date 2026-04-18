# Recipes

Copy-pasteable pipelines. Assumes `logseq` is on `$PATH` and a token is set via `$LOGSEQ_API_TOKEN`, `--token`, or `~/.config/claude/skills/logseq/state/config.json`.

## Table of contents

- Reading today / journals
- TODO aggregation
- Graph health
- Tags / backlinks
- Raw Datalog
- Properties
- Exports
- Block refs
- Cron / scripting
- Writes
- Inspection

## Reading today

```bash
# Today's journal as a tree
logseq today --tree --format md

# Fallback when today returns null (fresh mount quirk)
logseq page "$(date +'%b %-do, %Y')" --tree --format md

# Just top-level UUIDs
logseq today --uuids-only
```

## TODO aggregation

```bash
# All TODOs in the graph
logseq q '(task TODO DOING)' --format tree

# TODOs from the last 30 journals
logseq journals --last 30 --uuids-only \
  | xargs -n1 logseq block --format tree \
  | grep -E '^\s*-\s+(TODO|DOING)'

# TODO + page name via Datalog
logseq datalog '[:find ?name ?content
                 :where
                 [?b :block/marker "TODO"]
                 [?b :block/content ?content]
                 [?b :block/page ?p]
                 [?p :block/original-name ?name]]' --format table
```

## Graph health

```bash
logseq stats --broken-refs
logseq stats --orphans
logseq stats --format json
```

## Tags / backlinks

```bash
# Top 20 tags by frequency
logseq tags --sort freq --limit 20 --format table

# All blocks tagged with a page
logseq backlinks "Reading List" --format tree

# Deduped referring pages only
logseq linked-refs "Reading List" --format plain | sort -u

# Grouped linked references (Logseq UI panel shape)
logseq linked-refs "Reading List"

# Which pages cite X?
logseq q '(page-ref "Eventide")' --format plain | sort -u
```

## Raw Datalog

```bash
# Count blocks
logseq datalog '[:find (count ?b) . :where [?b :block/uuid _]]'

# Blocks in the last 7 days
NOW=$(date +%s000)
WEEK_AGO=$((NOW - 7 * 86400 * 1000))
logseq datalog "[:find (pull ?b [:block/uuid :block/content])
                 :in \$ ?from
                 :where [?b :block/created-at ?ts] [(>= ?ts ?from)]]" \
  --inputs "$WEEK_AGO" --format table

# Top 10 largest pages
logseq datalog '[:find ?name (count ?b)
                 :where [?p :block/name ?name] [?b :block/page ?p]]' \
  --format table --limit 10
```

## Properties

```bash
logseq prop-search status          # blocks with a property key
logseq prop-search status draft    # property = value

# All property keys in the graph
logseq datalog '[:find [?k ...]
                 :where
                 [?b :block/properties ?props]
                 [(keys ?props) ?ks]
                 [(identity ?ks) [?k ...]]]' --format plain | sort -u
```

## Exports

```bash
# Full page tree
logseq page "Reading List" --tree

# Page as markdown to file
logseq page "Reading List" --format md > /tmp/reading-list.md

# Dump January journals
for d in $(logseq datalog '[:find [?d ...]
                            :where
                            [?p :block/journal-day ?d]
                            [(>= ?d 20260101)] [(<= ?d 20260131)]]' \
            --format plain); do
  logseq page-by-journal-day "$d" --format md
done > /tmp/jan-2026.md
```

## Block refs

```bash
# Block by UUID with children
logseq block 69e30997-c335-4977-a97b-f9a62114888e --children

# All blocks citing a specific block
logseq refs-to-block 69e30997-c335-4977-a97b-f9a62114888e

# Resolve ((uuid)) refs inline when rendering
logseq page "Reading List" --resolve-refs --format md
```

## Cron / scripting

```bash
# Log daily block count
echo "$(date -Is) blocks=$(logseq datalog \
  '[:find (count ?b) . :where [?b :block/uuid _]]')" \
  >> ~/.local/share/logseq-metrics.log

# Mail daily broken refs (non-empty)
BROKEN=$(logseq stats --broken-refs --format plain)
[ -n "$BROKEN" ] && echo "$BROKEN" | mail -s "Logseq broken refs" you@example.com

# Today's journal → Claude summary
logseq today --format md | claude -p "summarize this day"
```

## Writes

All writes honor `--dry-run` (print POST body, do nothing) and `-y`/`--yes`.

```bash
logseq write page-create "Project Ideas" --property type=note
logseq write append "$(date +'%b %-do, %Y')" "- captured $(date +%H:%M)"
logseq write block-update 69e3...888e "new content" --yes
logseq write prop-set 69e3...888e status done

# Safe pattern: dry-run first
logseq write page-delete "Old Notes" --dry-run
logseq write page-delete "Old Notes" --yes
```

## Inspection

```bash
logseq raw --list                                   # all 123 methods
logseq raw logseq.Editor.getPage --args '["X"]'     # any method directly
logseq raw logseq.Editor.getPage --args '["X"]' --dry-run
logseq config show                                  # session state
```
