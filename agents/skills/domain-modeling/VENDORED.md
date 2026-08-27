Vendored from https://github.com/mattpocock/skills (MIT), `skills/engineering/`.

Skills here: `diagnosing-bugs`, `wayfinder`, `domain-modeling`.

Copied rather than installed as the `mattpocock-skills` plugin, to take only these
three instead of all ~22. Tradeoff: no auto-updates. To refresh:

    gh api "repos/mattpocock/skills/contents/skills/engineering/<skill>/SKILL.md" \
      --jq '.content' | base64 -d > ~/.config/agents/skills/<skill>/SKILL.md

The full plugin is in Claude Code's official marketplace if you ever want all of them:
`claude plugins install mattpocock-skills`.
