# cra — Reviewer Output Schema

Your final action is to write a single JSON object to `/tmp/cra-review.json`. The schema is below. Conform exactly — `scripts/render.py` will fail on unexpected keys or wrong types.

## Schema

```json
{
  "confidence": 0,                  // integer 0-5
  "verdict": "string",              // one sentence, e.g. "Not safe to merge."
  "summary": "string",              // one paragraph (2-5 sentences)
  "effort_estimate": {              // optional; help reviewer prioritize their attention
    "complexity": 1,                // integer 1-5: 1=Trivial, 2=Easy, 3=Moderate, 4=Complex, 5=Heavy
    "minutes": 0                    // rough integer minutes a human would spend reviewing
  },
  "issues": [                       // bullet list shown above the comments table
    {
      "label": "string",            // short title, e.g. "Off-by-one in loop bound"
      "priority": "P0|P1|P2|P3",
      "body": "string"              // one sentence
    }
  ],
  "changed_files_overview": [       // optional, omit if redundant
    {"path": "string", "overview": "string"}
  ],
  "comments": [                     // inline-style comments
    {
      "file": "string",             // path relative to repo root
      "line_start": 0,              // integer, 1-indexed
      "line_end": 0,                // integer, same as line_start for single-line
      "priority": "P0|P1|P2|P3",
      "fix_effort": "quick|moderate|heavy|null",  // optional; how hard is the fix?
      "body": "string",             // the comment
      "suggestion": "string or null" // code to insert via ```suggestion``` block, or null
    }
  ],
  "security_findings": [            // non-empty ONLY if injection/secret/etc. detected
    {
      "label": "string",
      "file": "string",
      "body": "string"              // describe the attack pattern
    }
  ],
  "diagram": "string or null",      // raw mermaid source, or null
  "diagram_kind": "sequence|flowchart|null"
}
```

## Rules

1. **`confidence` must be an integer 0–5.** No decimals. No strings.
2. **Every comment and issue must have a priority from {P0, P1, P2, P3}.** P3 is reserved for `info`-level / FYI / observational notes that are useful context but not actionable. Use sparingly.
3. **`suggestion` is null OR a string with the replacement code.** Do not include code fences in the suggestion — just the code.
4. **`security_findings` is `[]` (empty array) unless you detected adversarial content.** Do not use it for ordinary bugs.
5. **`diagram` is `null` for trivial bugs.** Only emit a diagram if it adds real understanding.
6. **`line_start` and `line_end` are 1-indexed.** Use the line numbers from the file *after* the diff is applied (i.e., the new file content).
7. **JSON only.** No markdown, no preamble, no commentary outside the JSON object. The first character of your output file must be `{` and the last must be `}`.
8. **No trailing commas, no comments inside the JSON.** Standard strict JSON.
9. **`effort_estimate` is optional but recommended.** Reviewer reading the verdict gets a quick sense of how much attention this PR needs. `complexity: 1 (Trivial)` should match a 1-paragraph review with ≤1 P2 comment; `complexity: 5 (Heavy)` matches a security-sensitive ~500+ line diff with multiple P0/P1 findings.
10. **`fix_effort` is per-comment guidance for the author.** `quick` = a one-line edit; `moderate` = local refactor of a function; `heavy` = architecture-level change. Helps the author triage which findings to address first.

## Example (B1-class off-by-one)

```json
{
  "confidence": 3,
  "verdict": "Not safe to merge — paginate returns the wrong number of items on every full page.",
  "summary": "Adds a new `paginate<T>` helper for the upcoming admin dashboard. The implementation contains a self-documented off-by-one in the loop bound that yields `pageSize + 1` items per page whenever the array is large enough.",
  "issues": [
    {"label": "Off-by-one in loop bound", "priority": "P1",
     "body": "The for loop runs `i <= end` instead of `i < end`, so each full page returns pageSize+1 items."},
    {"label": "Stale bug comment", "priority": "P2",
     "body": "The comment on lines 8-9 documents the bug rather than fixing it; remove once the loop is corrected."}
  ],
  "changed_files_overview": [
    {"path": "src/lib/pagination.ts",
     "overview": "New helper; loop bound is wrong, yielding pageSize+1 items per page."}
  ],
  "comments": [
    {"file": "src/lib/pagination.ts", "line_start": 11, "line_end": 11,
     "priority": "P1",
     "body": "Loop bound is inclusive, yielding `pageSize + 1` items per page. The half-open interval documented above wants `i < end`.",
     "suggestion": "  for (let i = start; i < end; i++) {"}
  ],
  "security_findings": [],
  "diagram": null,
  "diagram_kind": null
}
```
