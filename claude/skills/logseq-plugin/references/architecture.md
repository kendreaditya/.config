# Plugin Architecture

The minimal viable Logseq plugin is ~30 lines of TypeScript. Everything beyond is one of three patterns:

1. **Journal-page injection** — inject HTML next to `.references` on journal pages. Example: Resurface.
2. **Sidebar / header UI** — inject into `.cp__header` or `.left-sidebar-inner` via `provideUI`. Example: File Explorer.
3. **Slash commands + block macros** — register `logseq.Editor.registerSlashCommand` or macro renderers. (Not covered here; see `references/apis.md`.)

## Bootstrap lifecycle

Every plugin follows this shape:

```ts
// src/main.ts
import "@logseq/libs";
import cssText from "./styles.css?raw";
import { state } from "./state";

async function main() {
  // 1. Style first (before any render).
  logseq.provideStyle({ key: "my-plugin-styles", style: cssText });

  // 2. Load persisted settings.
  state.load(logseq.settings);

  // 3. Optional: log schema at startup to debug datascript issues early.
  await diagnoseSchema();

  // 4. First render / initial work.
  await run();

  // 5. Listeners for re-runs.
  logseq.App.onRouteChanged(async () => { await run(); });
  // plus MutationObserver, DB.onChanged, onCurrentGraphChanged, etc. as needed.
}

logseq.ready(main).catch(console.error);
```

The `logseq.ready(main)` wrapper is **required** — it waits until the Logseq host has finished wiring the plugin iframe + API surface before calling `main()`.

## State pattern

A singleton class with two tiers:

```ts
// src/state.ts
type Persisted = {
  sectionCollapsed?: boolean;
};

class State {
  sectionCollapsed = false;
  collapsedCards: Set<string> = new Set();   // transient

  load(settings: any): void {
    const s: Persisted = settings ?? {};
    this.sectionCollapsed = s.sectionCollapsed ?? false;
  }

  dump(): Persisted {
    return { sectionCollapsed: this.sectionCollapsed };
  }
}

export const state = new State();
```

`dump()` output is persisted to `logseq.settings` via `logseq.updateSettings(state.dump())`. Debounce the persist call (200ms) when the user is rapidly toggling.

Everything **not** in `Persisted` (like `collapsedCards`) is per-session transient. Clear transient sets at the top of `run()` — they accumulate stale UUIDs otherwise.

## Pattern 1: Journal-page injection

Used when the plugin adds content to the journal view (e.g. Resurface's "Resurfaced" section above Linked References).

**Detect the journal page.** Native selectors vary across builds — try all four:

```ts
function journalRoot(): HTMLElement | null {
  const doc = (window as any).top?.document ?? document;
  return doc.querySelector(".journal-item")
      ?? doc.querySelector(".journal.page")
      ?? doc.querySelector(".page.is-journals")
      ?? doc.querySelector(".page-inner-wrap.is-journals");
}
```

**Read the date from the DOM title, never from `Editor.getCurrentPage()`** (which returns null on fresh journal mounts):

```ts
function readJournalTitle(): string | null {
  const doc = (window as any).top?.document ?? document;
  const el = doc.querySelector(".journal-title h1.title, h1.title") as HTMLElement | null;
  return el?.textContent?.trim() ?? null;
}

function parseDate(name: string): Date | null {
  // ISO: 2026-04-17
  const iso = name.match(/^(\d{4})[-_](\d{2})[-_](\d{2})$/);
  if (iso) return new Date(+iso[1], +iso[2]-1, +iso[3]);
  // Pretty: Apr 17th, 2026
  const months = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"];
  const pretty = name.toLowerCase().match(/^([a-z]{3,})\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})$/);
  if (pretty) {
    const m = months.indexOf(pretty[1].slice(0,3));
    if (m >= 0) return new Date(+pretty[3], m, +pretty[2]);
  }
  return null;
}
```

**Watch for journal mount** — Logseq doesn't always fire `onRouteChanged` when you scroll-navigate between journals. MutationObserver + title-change check:

```ts
const obs = new MutationObserver(() => {
  const title = readJournalTitle();
  if (title && title !== lastRenderedTitle && isJournalPage()) run();
});
obs.observe(document.body, { childList: true, subtree: true });
```

**Inject.** Find `.references:not(.your-plugin-marker)`, walk up to its `.lazy-visibility` wrapper if present, and `insertAdjacentElement("beforebegin", el)`.

## Pattern 2: Sidebar / header UI

Used when the plugin adds persistent UI (e.g. File Explorer's left sidebar panel).

**Inject via `provideUI`** into known Logseq DOM slots:

```ts
const HEADER_SELECTOR = ".cp__header .l.drag-region";
const PANEL_SELECTOR = ".left-sidebar-inner > .flex.flex-col.wrap";

logseq.provideUI({
  key: "my-header-button",
  path: HEADER_SELECTOR,
  template: `<a data-on-click="togglePanel"><svg>...</svg></a>`,
  reset: true,
});

logseq.provideUI({
  key: "my-panel",
  path: PANEL_SELECTOR,
  template: panelHtml,
  reset: true,
});
```

**Route clicks via `provideModel`.** Elements with `data-on-click="methodName"` invoke the matching method on the model:

```ts
logseq.provideModel({
  togglePanel() { state.panelOpen = !state.panelOpen; rerender(); },
  openPage(e: any) { logseq.App.pushState("page", { name: e.dataset.page }); },
  toggleFolder(e: any) { state.toggleFolder(e.dataset.path); rerender(); },
});
```

Rerender by calling `provideUI` again with the same `key` — `reset: true` replaces the previous template.

**Top-frame DOM access.** Plugin code runs in an iframe; `document` is the iframe's. To reach the host (Logseq's main window):

```ts
const doc = (window as any).top?.document ?? document;
const apis = (window as any).top?.apis;   // Electron IPC bridge for file ops
```

## Delegated click handler (Pattern 1 alternative)

When injecting raw HTML (not using `provideUI`), use a single delegated listener:

```ts
type ClickAction =
  | { type: "section-toggle" }
  | { type: "page-nav"; name: string }
  | { type: "block-nav"; uuid: string };

function resolveAction(target: HTMLElement): ClickAction | null {
  if (target.closest('[data-role="section-toggle"]')) return { type: "section-toggle" };
  const pageRef = target.closest("a.page-ref") as HTMLElement | null;
  if (pageRef) return { type: "page-nav", name: pageRef.dataset.page ?? "" };
  // ...
  return null;
}

el.addEventListener("click", (e) => {
  const target = e.target as HTMLElement;
  if (target.closest('a[href^="http"]')) return;   // let external links through
  const action = resolveAction(target);
  if (!action) return;
  e.preventDefault();
  e.stopPropagation();
  handleAction(action);
});
```

## Native-looking HTML

Plugins can't call Logseq's renderer — implement your own minimal markdown → HTML and use Logseq's native class names so the user's theme styles it for free:

- Wikilinks `[[Page]]` → `<span class="page-reference"><span class="bracket">[[</span><a class="page-ref">Page</a><span class="bracket">]]</span></span>`
- Tags `#tag` → `<a class="tag">#tag</a>`
- Blocks → `.ls-block > .block-main-container > .block-content-wrapper > .block-content.inline`
- External links → `<a class="external-link" target="_blank">`

`references/gotchas.md` covers the surprises (whitespace inside `.block-content`, chevron positioning, etc.).

## File layout convention

```
src/
├── main.ts       entry + pipeline orchestration
├── state.ts      persistent + transient state
├── render.ts     HTML emitter (if Pattern 1/2)
├── inject.ts     DOM placement + click delegation (if Pattern 1)
├── query.ts      datascript queries + defensive readers (if reading DB)
├── mdParser.ts   minimal markdown → HTML (if rendering block content)
└── styles.css    scoped CSS (imported via ?raw and fed to provideStyle)
```

Not every plugin needs all of these. Start with `main.ts + state.ts + styles.css` and grow.
