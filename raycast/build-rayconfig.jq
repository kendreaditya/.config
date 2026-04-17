def now_iso:
  (now | strftime("%Y-%m-%dT%H:%M:%SZ"));

{
  raycast_version: "1.104.12",

  builtin_package_rootSearch: {
    rootSearch: (
      [.hotkeys[] | (
        if .target_path then
          { key: .target_key, hotkey: .hotkey, type: .type, path: .target_path }
        else
          { key: .target_key, hotkey: .hotkey, type: .type }
        end
      )]
      +
      [.aliases[] | (
        if .target_path then
          { key: .target_key, alias: .alias, type: "systemApp", path: .target_path }
        else
          { key: .target_key, alias: .alias, type: "command" }
        end
      )]
    ),
    provider_schemaVersion: 1
  },

  builtin_package_snippets: {
    snippets: [
      .snippets[] | {
        name: .name,
        text: .text,
        alias: .keyword,
        category: "text",
        createdAt: now_iso,
        modifiedAt: now_iso
      }
    ],
    provider_schemaVersion: 1
  }
}
