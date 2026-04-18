# Logseq Plugin API Cheatsheet

The full `@logseq/libs` surface is large. This covers what Resurface + File Explorer actually use — ~90% of what plugins need.

Top-level object is `logseq` (global, provided by `@logseq/libs`). Sub-namespaces: `DB`, `Editor`, `App`, `Assets`, `FileStorage`.

## Core

| API | Purpose | Example |
|---|---|---|
| `logseq.ready(fn)` | Register plugin entrypoint; fires when API surface is ready. Return value is awaitable. | `logseq.ready(main).catch(console.error)` |
| `logseq.settings` | Object snapshot of this plugin's persisted settings (from last `updateSettings` call). | `state.load(logseq.settings)` |
| `logseq.updateSettings(obj)` | Merge + persist settings for this plugin. | `logseq.updateSettings({ sectionCollapsed: true })` |
| `logseq.useSettingsSchema(schema)` | Optional: register a formal settings schema so Logseq renders a settings UI. | — |
| `logseq.provideStyle({ key, style })` | Inject scoped CSS into Logseq's main window. `key` dedupes across reloads. | `logseq.provideStyle({ key: "my-plugin", style: cssText })` |
| `logseq.provideUI({ key, path, template, reset })` | Inject HTML into a Logseq DOM slot selected by `path`. | Sidebar panel |
| `logseq.provideModel(obj)` | Register click handlers for `data-on-click` attributes in `provideUI` templates. | `{ openPage(e) { ... } }` |
| `logseq.hideMainUI() / showMainUI()` | Hide or show the plugin's own modal/popup window (if the plugin uses one). | — |

## `logseq.DB`

| API | Purpose | Notes |
|---|---|---|
| `DB.datascriptQuery(q)` | Run a Datalog query against the user's graph. Returns an array (or single value for scalar queries). | **Returns flat, namespace-stripped pull keys.** See `references/datascript.md`. |
| `DB.onChanged(cb)` | Fire `cb` on any DB change. Debounce the callback (e.g. 500ms) if you rerender on it — Logseq batches mutations into rapid bursts. | Used by File Explorer for live page/file tree updates. |

## `logseq.Editor`

**Reads:**

| API | Returns | Caveats |
|---|---|---|
| `Editor.getBlock(uuid, { includeChildren })` | `BlockEntity \| null` | Use `includeChildren: true` to hydrate the subtree. |
| `Editor.getPage(nameOrId)` | `PageEntity \| null` | Try both original-case and lowercased name. |
| `Editor.getAllPages()` | `PageEntity[]` | Use for building page trees / namespace hierarchies. |
| `Editor.getCurrentPage()` | `PageEntity \| null` | **Returns `null` on fresh journal mounts.** Read the DOM title instead for journal detection. |
| `Editor.getCurrentBlock()` | `BlockEntity \| null` | — |
| `Editor.getTodayPage()` | `PageEntity` | Convenience — same as `getPage(formatDate(today))`. |
| `Editor.getPageBlocksTree(nameOrId)` | `BlockEntity[]` | Returns root-level blocks with children hydrated. |

**Writes:**

| API | Purpose |
|---|---|
| `Editor.insertBlock(parentUuid, content, opts)` | Insert new block under a parent. |
| `Editor.appendBlockInPage(page, content)` | Append a new top-level block to a page. |
| `Editor.updateBlock(uuid, content)` | Change block content. |
| `Editor.removeBlock(uuid)` | Delete block. |
| `Editor.createPage(name, properties, opts)` | Create a new page. |
| `Editor.renamePage(old, new)` | Preserves `[[backlinks]]`. Use for any page rename that should not break links. |
| `Editor.deletePage(name)` | Preserves link integrity. |

**Navigation:**

| API | Purpose |
|---|---|
| `Editor.scrollToBlockInPage(uuid)` | Navigate to the block's page and scroll it into view. Our preferred "click handler" target for injected block cards. |
| `Editor.openInRightSidebar(uuid)` | Opens the block as a pane in the right sidebar (useful when you want the user to keep their current page). |

**Slash / macro registration:**

| API | Purpose |
|---|---|
| `Editor.registerSlashCommand(name, callback)` | Register `/name` command. |
| `Editor.registerBlockContextMenuItem(name, callback)` | Register a right-click menu item on blocks. |

## `logseq.App`

| API | Purpose |
|---|---|
| `App.pushState(name, params)` | Navigate to a page. `pushState("page", { name })` for pages, `pushState("page", { name: "#mytag" })` for tags. |
| `App.replaceState(...)` | Like pushState but doesn't add to history. |
| `App.onRouteChanged(cb)` | Fire when the route changes. **Not always reliable on journal day switches** — pair with a MutationObserver. |
| `App.onCurrentGraphChanged(cb)` | Fire when the user switches graphs. Reload state; the DB is a completely different graph. |
| `App.onSidebarVisibleChanged(cb)` | Fire when left sidebar opens/closes. |
| `App.getCurrentGraph()` | `{ name, path, url }`. `path` is the filesystem path for file graphs. |
| `App.getUserConfigs()` | `{ preferredDateFormat, ... }`. Use for the user's preferred date format. |
| `App.setLeftSidebarVisible(bool)` / `setRightSidebarVisible(bool)` | Programmatically toggle the sidebars. |
| `App.invokeExternalCommand(cmd)` | Run any internal Logseq command by id. |

## `logseq.Assets`

| API | Purpose |
|---|---|
| `Assets.makeUrl(path)` | Convert a relative path in the user's assets dir into a file:// URL you can use in `<img>`. |
| `Assets.listFiles()` | Enumerate plugin-owned assets shipped in the plugin zip. |

## `logseq.FileStorage`

| API | Purpose |
|---|---|
| `FileStorage.setItem(key, value)` / `getItem(key)` / `removeItem(key)` | Per-plugin key-value storage (separate from `logseq.settings`). Use for bigger-than-settings blobs. |

## Top-frame IPC bridge (Electron-only)

For filesystem operations in a file graph (File Explorer pattern):

```ts
const apis = (window as any).top?.apis;
// apis.doAction([name, ...args]) dispatches into Electron's IPC.
// Supported actions include: openFileInFolder, showMessage, readdir, etc.
await apis?.doAction(["openFileInFolder", absolutePath]);
```

This is **Electron-specific** — web versions of Logseq won't have `window.top.apis`. Guard all calls and degrade gracefully.

## Full type definitions

`@logseq/libs` ships `.d.ts` files. In a plugin repo: `node_modules/@logseq/libs/dist/LSPlugin.d.ts` has the canonical shapes of `BlockEntity`, `PageEntity`, `AppUserConfigs`, etc. Read them when the API table above is incomplete.
