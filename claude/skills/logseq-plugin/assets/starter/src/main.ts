import "@logseq/libs";
import cssText from "./styles.css?raw";

async function main(): Promise<void> {
  // Scoped styles — inject once at startup.
  (logseq as any).provideStyle({ key: "TODO-plugin-id-styles", style: cssText });

  // Hello-world log. Grep "[TODO-plugin-id]" in DevTools to confirm the
  // plugin loaded.
  console.log("[TODO-plugin-id] ready");

  // TODO: wire up the plugin. Pick a pattern from
  // ~/.config/claude/skills/logseq-plugin/references/architecture.md:
  //   - Journal-page injection (MutationObserver + readJournalTitleFromDom)
  //   - Sidebar/header UI (logseq.provideUI + logseq.provideModel)
  //   - Slash command / block macro (logseq.Editor.registerSlashCommand)
}

(logseq as any).ready(main).catch((e: unknown) => {
  console.error("[TODO-plugin-id] ready failed:", e);
});
