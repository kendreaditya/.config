# Logseq HTTP API (0.10.15)

## Server surface

- Endpoint: `POST http://127.0.0.1:12315/api`
- Auth: `Authorization: Bearer <token>` (format per `src/electron/electron/server.cljs:75-81`)
- Body: `{"method": "logseq.Namespace.methodName", "args": [...]}`
- Bind: `127.0.0.1` only by default (`server.cljs:19`). Port configurable via `:server/port`.
- CORS: `*` — accepts any origin (`server.cljs:138`).
- Namespace routing: `logseq.X.methodName` is stripped; only `ui`, `git`, `assets` tags get preserved as snake_case prefixes (e.g. `logseq.UI.showMsg` → `ui_show_msg`, `logseq.Editor.getPage` → `get_page`). See `server.cljs:62-72`.
- Tested against Logseq Desktop 0.10.15. `get_app_info` returns `{"version":"0.10.15"}`.

## Error responses

- HTTP 200 + `{"error": "MethodNotExist: <name>"}` → method not wired at runtime (quirk: not 404).
- HTTP 200 + `{"error": "<message>"}` → method threw (e.g. bad UUID, missing page).
- HTTP 400 → body missing `:method`.
- HTTP 401 → missing/bad bearer token.
- HTTP 500 → internal exception (rare).

## Methods

Grouped by domain. Arg names are from `src/main/logseq/api.cljs`. Return shapes marked *(probed)* are confirmed live; others are *(inferred)* from source.

### App / metadata
- `get_app_info()` → `{version: string}` *(probed)*
- `get_current_graph()` → `{url, name, path}` or `null` if on local demo *(probed, api.cljs:147)*
- `get_user_configs()` → `{preferredLanguage, preferredThemeMode, preferredFormat, preferredWorkflow, preferredTodo, preferredDateFormat, preferredStartOfWeek, currentGraph, showBrackets, enabledJournals, enabledFlashcards, me}` *(probed, api.cljs:95)*
- `get_current_graph_configs([...keys])` → full config map or nested value *(api.cljs:112)*
- `set_current_graph_configs(configsMap)` → nil *(api.cljs:118)*
- `get_current_graph_favorites()` → `string[]` (page names) *(probed)*
- `get_current_graph_recent()` → `string[]` (page names) *(probed)*
- `get_current_graph_templates()` → `{templateName: BlockEntity, ...}` *(probed, api.cljs:139)*
- `get_state_from_store(path)` → any *(api.cljs:67, path is string or array, `@` prefix keeps as string key)*
- `set_state_from_store(path, value)` → nil *(api.cljs:78)*
- `log_app_state(path?)` → state value *(sdk/debug.cljs:5)*
- `force_save_graph()` → `true` *(api.cljs:1012)*
- `version()` → `"20230330"` — SDK version constant, not app version *(sdk/core.cljs:4)*

### Page (read)
- `get_current_page()` → `PageEntity | null`. **Returns null on fresh journal mounts in 0.10.x** — use `get_page("<today>")` or DOM title instead. *(probed)*
- `get_page(idOrName)` → `PageEntity | null` *(probed, api.cljs:542)*
- `get_all_pages(repo?)` → `PageEntity[]` *(probed, api.cljs:550)*
- `get_page_blocks_tree(idOrName)` → `BlockEntity[]` (nested via `children`) *(probed, api.cljs:769)*
- `get_current_page_blocks_tree()` → `BlockEntity[]` *(api.cljs:760)*
- `get_page_linked_references(nameOrUuid)` → `[[PageEntity, BlockEntity[]], ...]` — array of `[refPage, blocksOnThatPageRefingThis]` pairs *(probed, api.cljs:777)*
- `get_pages_from_namespace(ns)` → `PageEntity[]` (flat list under prefix) *(api.cljs:787)*
- `get_pages_tree_from_namespace(ns)` → nested namespace tree *(api.cljs:793)*

### Page (write)
- `create_page(name, properties?, {redirect?, createFirstBlock?, format?, journal?})` → `PageEntity` *(api.cljs:555)*
- `delete_page(name)` → promise, resolves on completion *(api.cljs:574)*
- `rename_page(oldName, newName)` → nil *(api.cljs:578)*

### Block (read)
- `get_block(uuid, {includeChildren?})` → `BlockEntity | null`; `children` populated when `includeChildren=true` *(probed, api.cljs:702, delegates to logseq.api.block)*
- `get_current_block(opts?)` → `BlockEntity | null` — currently edited/selected block *(api.cljs:704)*
- `get_previous_sibling_block(uuid)` → `BlockEntity | null` *(api.cljs:714)*
- `get_next_sibling_block(uuid)` → `BlockEntity | null` *(api.cljs:721)*
- `get_selected_blocks()` → `BlockEntity[]` or null *(api.cljs:528)*

### Block (write)
- `insert_block(srcUuidOrPageName, content, {before?, sibling?, focus?, customUUID?, properties?, autoOrderedList?})` → new `BlockEntity` *(api.cljs:603)*
- `insert_batch_block(parentUuid, batch, {sibling?, keepUUID?, before?})` → nil. `batch` is an array of `{content, properties?, children?}` *(api.cljs:649)*
- `append_block_in_page(uuidOrPageName, content, opts)` → new `BlockEntity` *(api.cljs:830)*
- `prepend_block_in_page(uuidOrPageName, content, opts)` → new `BlockEntity` *(api.cljs:814)*
- `update_block(uuid, content, opts?)` → nil *(api.cljs:676)*
- `remove_block(uuid, opts?)` → nil (deletes children too) *(api.cljs:668)*
- `move_block(srcUuid, targetUuid, {before?, children?})` → nil *(api.cljs:686)*
- `set_block_collapsed(uuid, {flag})` → nil; `flag` is boolean or `"toggle"` *(api.cljs:728)*
- `new_block_uuid()` → string UUID *(api.cljs:588)*
- `set_blocks_id(uuids[])` → nil *(api.cljs:1017)*

### Block properties
- `get_block_property(uuid, key)` → scalar *(api.cljs:750)*
- `get_block_properties(uuid)` → `{key: value, ...}` *(api.cljs:755)*
- `upsert_block_property(uuid, key, value)` → nil *(api.cljs:742)*
- `remove_block_property(uuid, key)` → nil *(api.cljs:746)*

### Editor (interactive / DOM state)
- `check_editing()` → edit block UUID string or `false` *(api.cljs:495)*
- `exit_editing_mode(select?)` → nil *(api.cljs:500)*
- `edit_block(uuid, {pos?})` → nil; `pos` is int or `"max"` *(api.cljs:596)*
- `select_block(uuid)` → nil *(api.cljs:591)*
- `insert_at_editing_cursor(content)` → nil *(api.cljs:505)*
- `restore_editing_cursor()` → nil *(api.cljs:512)*
- `get_editing_cursor_position()` → `{left, top, pos, rect}` *(api.cljs:519)*
- `get_editing_block_content()` → string *(api.cljs:524)*
- `save_focused_code_editor_content()` → nil *(api.cljs:178)*

### Search / query
- `search(q)` → `{blocks, pages, pages-content, files, has-more?}`. Snippets contain PFTS highlight markers `$pfts_2lqh>...<pfts_2lqh$` *(probed, api.cljs:1000)*
- `q(dslString)` → `any[]`. Logseq simplified DSL: `(page "X")`, `(task TODO DOING)`, `(page-ref "X")`, `(tag "X")`, `(and ...)`. *(probed, api.cljs:859)*
- `datascript_query(queryStr, ...inputs)` → raw Datalog result; shape depends on `:find` clause *(probed, api.cljs:866)*
- `custom_query(queryStr)` → flattened result of a Logseq advanced query map *(api.cljs:884)*

### Templates
- `get_template(name)` → `BlockEntity` *(api.cljs:966)*
- `exist_template(name)` → bool *(api.cljs:979)*
- `insert_template(targetUuid, templateName)` → nil *(api.cljs:973)*
- `create_template(targetUuid, templateName, {overwrite?})` → nil *(api.cljs:983)*
- `remove_template(name)` → nil *(api.cljs:994)*

### UI (prefix `ui_` preserved)
- `ui_show_msg(content, status?, {key?, timeout?})` → key string. `content` may start with `[:` for Hiccup. *(sdk/ui.cljs:17)*
- `ui_close_msg(key)` → nil *(sdk/ui.cljs:33)*
- `ui_query_element_rect(selector)` → `DOMRect` as JSON *(sdk/ui.cljs:38)*
- `ui_query_element_by_id(id)` → `"TAG#id"` or `false` *(sdk/ui.cljs:43)*
- `ui_check_slot_valid(slot)` → bool *(sdk/ui.cljs:48)*
- `ui_resolve_theme_css_props_vals(props)` → `{prop: val}` *(sdk/ui.cljs:53)*

### Navigation / window
- `push_state(k, params, query)` → nil *(api.cljs:460)*
- `replace_state(k, params, query)` → nil *(api.cljs:470)*
- `open_external_link(url)` → nil (must be http/https) *(api.cljs:423)*
- `open_in_right_sidebar(blockIdOrUuid)` → nil *(api.cljs:581)*
- `set_left_sidebar_visible(flag)` → nil; bool or `"toggle"` *(api.cljs:438)*
- `set_right_sidebar_visible(flag)` → nil *(api.cljs:446)*
- `clear_right_sidebar_blocks({close?})` → nil *(api.cljs:453)*
- `show_themes()` → nil (opens theme picker) *(api.cljs:155)*
- `set_theme_mode(mode)` → nil; `"dark"|"light"` *(api.cljs:159)*
- `relaunch()` / `quit()` → nil *(api.cljs:415, 419)*
- `exec_command(type, ...args)` → nil (`type` must start with `logseq.`) *(api.cljs:428)*
- `invoke_external_command(type, ...args)` → nil *(api.cljs:428)*

### Git (prefix `git_` preserved)
- `git_exec_command(args[])` → promise of stdout *(sdk/git.cljs:9)*
- `git_load_ignore_file()` → `.gitignore` content *(sdk/git.cljs:14)*
- `git_save_ignore_file(content)` → nil *(sdk/git.cljs:23)*
- `exec_git_command(args[])` → promise *(api.cljs:907, duplicate non-prefixed path)*

### Assets (prefix `assets_` preserved)
- `assets_make_url(path)` → asset URL string *(sdk/assets.cljs:10)*
- `assets_built_in_open(assetFile)` → nil (opens in PDF viewer for pdf) *(sdk/assets.cljs:17)*
- `make_asset_url(path)` → non-prefixed alias *(api.cljs:918)*

### Plugin runtime (rarely useful from CLI)
- `__install_plugin(manifest)` → promise *(api.cljs:851)*
- `install-plugin-hook(pid, hook, opts)` *(api.cljs:54)*
- `uninstall-plugin-hook(pid, hookOrAll)` *(api.cljs:58)*
- `should-exec-plugin-hook(pid, hook)` → bool *(api.cljs:62)*
- `register_plugin_slash_command(pid, cmdActions)` *(api.cljs:342)*
- `register_plugin_simple_command(pid, cmdAction, palette?)` *(api.cljs:349)*
- `unregister_plugin_simple_command(pid)` *(api.cljs:384)*
- `register_plugin_ui_item(pid, type, opts)` *(api.cljs:408)*
- `register_search_service(pid, name, opts)` *(api.cljs:400)*
- `unregister_search_services(pid)` *(api.cljs:404)*
- `validate_external_plugins(urls)` *(api.cljs:848)*
- `get_external_plugin(pid)` → manifest JSON *(api.cljs:480)*
- `invoke_external_plugin_cmd(pid, group, key, args)` — `group` is `"models"` or `"commands"` *(api.cljs:485)*
- `set_focused_settings(pid)` → nil *(api.cljs:1006)*

### Plugin storage / config (file I/O in plugin dotdir)
- `load_plugin_config(path)` → package.json string *(api.cljs:163)*
- `load_plugin_readme(path)` → readme.md string *(api.cljs:167)*
- `save_plugin_config(path, data)` → nil *(api.cljs:171)*
- `load_user_preferences()` → parsed preferences.json *(api.cljs:312)*
- `save_user_preferences(data)` → nil *(api.cljs:322)*
- `load_plugin_user_settings()` → `[path, data]` *(api.cljs:330)*
- `save_plugin_user_settings(key, data)` → nil *(api.cljs:334)*
- `unlink_plugin_user_settings(key)` → nil *(api.cljs:339)*
- `write_user_tmp_file(file, content)` → abs path *(api.cljs:252)*
- `write_plugin_storage_file(pid, file, content, assets?)` *(api.cljs:256)*
- `read_plugin_storage_file(pid, file, assets?)` → content *(api.cljs:264)*
- `unlink_plugin_storage_file(pid, file, assets?)` *(api.cljs:272)*
- `exist_plugin_storage_file(pid, file, assets?)` → bool *(api.cljs:280)*
- `clear_plugin_storage_files(pid, assets?)` → nil *(api.cljs:291)*
- `list_plugin_storage_files(pid, assets?)` → `string[]` *(api.cljs:299)*

### Experimental
- `exper_load_scripts(pid, ...scripts)` *(api.cljs:921)*
- `exper_register_fenced_code_renderer(pid, type, opts)` *(api.cljs:936)*
- `exper_register_extensions_enhancer(pid, type, enhancer)` *(api.cljs:943)*
- `exper_request(pid, options)` → reqId *(api.cljs:951)*
- `http_request_abort(reqId)` → nil *(api.cljs:961)*

### Graph export
- `download_graph_db()` — triggers browser download of transit file *(api.cljs:891)*
- `download_graph_pages()` — triggers zip export *(api.cljs:902)*

### Unwired / runtime-only at remote surface
- `list_files_of_current_graph(exts)` — declared at `sdk/assets.cljs:12` but **returns `MethodNotExist: list_files_of_current_graph`** over HTTP in 0.10.15. Likely only reachable in-process.

## Cross-reference

Full method name list in `/Users/kendreaditya/.config/claude/skills/logseq/scripts/_known_methods.txt` (123 entries). Each appears in either `api.cljs` or `sdk/*.cljs`. Agent contract at `scripts/AGENT_CONTRACT.md`.
