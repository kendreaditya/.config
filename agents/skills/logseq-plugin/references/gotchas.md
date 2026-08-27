# Gotchas

Real bugs from real plugins, with root cause and fix. Read before modifying DOM injection, query code, or CSS.

## 1. `Editor.getCurrentPage()` returns null on journal mounts

**Symptom.** Plugin bails before doing anything. `Editor.getCurrentPage()` returns `null` even with the journal fully visible.

**Root cause.** On Electron desktop Logseq, `getCurrentPage()` only populates when the user explicitly navigated via a page link. Opening via the calendar sidebar or the initial mount leaves it null. Undocumented and version-dependent.

**Fix.** Read from the DOM title instead:

```ts
function readJournalTitle(): string | null {
  const doc = (window as any).top?.document ?? document;
  const el = doc.querySelector(".journal-title h1.title, h1.title") as HTMLElement | null;
  return el?.textContent?.trim() ?? null;
}
```

Parse both ISO (`2026-04-17`) and pretty (`Apr 17th, 2026`) formats. Do not re-add `Editor.getCurrentPage()` as the primary source.

## 2. `datascriptQuery` flat namespace-stripped keys

Covered in depth in `references/datascript.md`. TL;DR: `pull.uuid` not `pull["block/uuid"]`. Add defensive fallbacks and run `diagnoseSchema` on startup.

## 3. Journal root selector varies across builds

**Symptom.** "Today's journal" detected; "yesterday's journal in a scrolling stack" not.

**Root cause.** Different selectors for different journal states:
- Today: `.journal-item > .journal.page`
- Direct-nav to past: `.page.is-journals`

**Fix.** Try all four in order:

```ts
function journalRoot(): HTMLElement | null {
  const doc = (window as any).top?.document ?? document;
  return doc.querySelector(".journal-item")
      ?? doc.querySelector(".journal.page")
      ?? doc.querySelector(".page.is-journals")
      ?? doc.querySelector(".page-inner-wrap.is-journals");
}
```

Add new selectors; never replace. False positives are caught by the next step (date parse).

## 4. `.references` is a sibling of `.journal.page`, not a child

**Symptom.** `root.querySelector('.references')` returns `null` even though Linked References is clearly on the page.

**Root cause.** `.references` lives as a sibling of `.journal.page` inside `.journal-item`, not a descendant of `.journal.page`.

**Fix.** Two layers:

```ts
const refs = root.querySelector(".references:not(.my-plugin-marker)")
          ?? doc.querySelector(".references:not(.my-plugin-marker)");
```

Also walk up to `.lazy-visibility` if present and insert `beforebegin` on the wrapper, not on `.references` itself, so you survive its re-mounts.

## 5. Chevron needs inline `margin-left: -30px`, not a CSS class

**Symptom.** Fold chevrons render inside card padding instead of the left gutter.

**Root cause.** `.block-control` relies on flex-parent + sibling-bullet layout to size and position. Without that context, it collapses to zero width and renders in-flow. External CSS rules lose specificity fights with themes.

**Fix.** Inline style directly on the `<a>`:

```ts
const CTRL_STYLE = "width: 14px; height: 16px; margin-left: -30px;";
// <a class="block-control" style="${CTRL_STYLE}">...
```

Do not "clean this up" into an external CSS rule. Inline survives theme overrides.

## 6. Transient state accumulates stale UUIDs

**Symptom.** `collapsedCards: Set<string>` grows without bound as the user navigates between pages. Eventually a memory concern; earlier, a correctness issue (stale UUID collides with a new card).

**Fix.** `state.collapsedCards.clear()` at the top of every `run()` / `rerender()`. Anything you don't explicitly persist in `dump()` should be treated as "lives for this view only."

## 7. `white-space: pre-wrap` on `.block-content` renders template-literal whitespace

**Symptom.** Blocks display with mysterious 100-200px of empty space below the text. DevTools shows `.block-content.inline` is ~200px tall but the visible text is only 3 lines (~72px).

**Root cause.** Native CSS sets `.block-content { white-space: pre-wrap; }` so the editor preserves user-typed whitespace. Plugin code using template literals emits newlines + indentation between sibling divs inside `.block-content`. pre-wrap renders each newline as a visible line break.

**Fix.** Either override the white-space rule in your scoped CSS:

```css
.my-plugin-refs .block-content {
  white-space: normal;
}
```

Or strip whitespace from your template between `<div>` siblings. Both belts are fine; CSS override is simpler.

## 8. `.ls-foldable-*` classes are master-only

**Symptom.** You target master branch's foldable DOM (`.ls-foldable-title`, `.ls-foldable-title-control`, `.ls-foldable-content`, `.is-collapsed`) and the chevron ends up at the wrong x-position in stable Logseq 0.10.x.

**Root cause.** Stable 0.10 uses a simpler shape:

```html
<div class="content">
  <div class="flex-1 flex-row foldable-title">
    <div class="flex flex-row items-center">
      <a class="block-control" style="width:14px; height:16px; margin-left:-30px">
        <span class="control-show cursor-pointer">
          <span class="rotating-arrow not-collapsed">{svg}</span>
        </span>
      </a>
      {header}
    </div>
  </div>
</div>
<div class="hidden|initial">{body}</div>
```

The master-only classes (`ls-foldable-title-control { margin-left: -27px }`, `ls-foldable-content { display: grid; grid-template-rows: 1fr; }`) don't exist in the 0.10 theme CSS, so your rules don't fire and positioning is wrong.

**Fix.** Target 0.10's shape unless you know the user is on a DB-based beta. The starter template uses 0.10 shapes.

## 9. Plugin HTML can't be made inline-editable

**Symptom.** User expects to edit block content inside an injected section. Typing in the injected block does nothing.

**Root cause.** Logseq's editor owns its own React-stateful DOM tree. Anything you inject via `insertAdjacentElement` or `provideUI` lives outside that tree.

**Fix.** On click, call `logseq.Editor.scrollToBlockInPage(uuid)` to jump to the source page where the block has its native editable rendering. Or use `logseq.Editor.openInRightSidebar(uuid)` to open the editable version in the sidebar while keeping the user's current page.

## 10. Iframe vs top-frame DOM

Plugin code runs in an iframe. `document` refers to the iframe's document, not Logseq's main window. For DOM injection, querying, or IPC, reach through `window.top`:

```ts
const doc = (window as any).top?.document ?? document;
const apis = (window as any).top?.apis;   // Electron IPC (may be undefined on web)
```

Always use the `?? document` fallback so the plugin works in reduced-permission contexts.

## 11. `onRouteChanged` doesn't fire for every journal day switch

**Symptom.** User scroll-navigates between journals. The plugin doesn't re-render.

**Root cause.** Logseq sometimes switches the rendered journal without emitting a route change (scroll-triggered loads, calendar picks).

**Fix.** Pair `onRouteChanged` with a MutationObserver that detects title changes:

```ts
const obs = new MutationObserver(() => {
  const title = readJournalTitle();
  if (title && title !== lastTitle && isJournalPage()) run();
});
obs.observe(document.body, { childList: true, subtree: true });
```

## 12. `logseq.provideStyle` keys are scoped per plugin, not global

Using the same `key` string from two different plugins doesn't collide — each plugin has its own namespace. But using the same `key` twice within the same plugin replaces the previous style (which is what you want for hot-reload during dev).
