# TODO Plugin Title

TODO: one-paragraph description.

## Install

### From the marketplace (once published)

Logseq → Plugins → Marketplace → search "TODO Plugin Title".

### From source

```bash
git clone https://github.com/TODO/TODO-plugin-id.git
cd TODO-plugin-id
npm install
npm run build
```

In Logseq Desktop: Settings → Advanced → Developer mode (enable) → top-right ⋯ → Plugins → Load unpacked plugin → select this folder.

## Develop

```bash
npm run dev   # vite build --watch
```

After each rebuild, reload the plugin from the Plugins page (the reload icon next to the plugin name).

Console logs appear in Logseq's main DevTools (`Cmd+Opt+I` / `Ctrl+Shift+I`), prefixed with `[TODO-plugin-id]`.

## Release

Tag a version and push:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The `.github/workflows/release.yml` workflow will build, zip the plugin, and attach `TODO-plugin-id.zip` to a new GitHub Release.

## License

MIT
