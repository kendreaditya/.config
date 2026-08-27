---
name: agent-upload
description: "Upload a local file — screenshot, screen recording, log, PDF, build artifact, archive — to the user's public file host and return a public URL. Use when the user asks to upload a file, share a file, get a link for a file, show them a recording or screenshot, or when a file needs to be embedded in a PR description, issue, or Slack message. Triggers: 'upload this', 'give me a link', 'share that screenshot', 'embed this video in the PR', 'agent-upload'."
---

# agent-upload

Upload any local file to the user's R2 bucket and get back a public URL.

The point of this skill is **communication, not capability**. It exists so you can
show Aditya a real artifact — the actual recording, the actual screenshot, the actual
failing log — instead of describing it in prose. Reach for it whenever a link would
be more useful than a paragraph.

## Usage

```bash
~/.config/agents/skills/agent-upload/upload.sh <file> [remote-name]
```

Prints one line: the public URL. Use only the file's base name — the script slugifies
it and appends a random suffix, so names do not need to be unique.

```bash
$ upload.sh /tmp/login-flow.mov
https://pub-abc123.r2.dev/login-flow-4f9c2a.mov
```

## When to use it proactively

Don't wait to be asked. Upload when:

- You recorded or screenshotted something and the user isn't at that machine.
- You're filing a PR that shows a visual change — attach the video/screenshot.
- A log or trace is too long to paste but the user may want to read it.
- The user is on their phone and asks what a change looks like.

## Embedding in GitHub

Markdown image syntax renders video inline on GitHub too:

```markdown
![login flow](https://pub-abc123.r2.dev/login-flow-4f9c2a.mov)
```

For a lighter preview, convert to GIF first:

```bash
ffmpeg -i in.mov -vf "fps=12,scale=900:-1:flags=lanczos" -loop 0 out.gif
```

## If it is not configured

If `AGENT_UPLOAD_BUCKET` or `AGENT_UPLOAD_BASE_URL` is unset, the script exits with
an error. **Tell the user to run setup — never guess a bucket name or invent a URL.**

```bash
~/.config/agents/skills/agent-upload/setup.sh
```

Setup needs a browser login and one Cloudflare dashboard click, so the user must run
it themselves. If they ask you to, walk them through it rather than trying to
automate the dashboard step.

## Notes

- Everything uploaded is **public to anyone with the link**. Do not upload secrets,
  `.env` files, credentials, customer data, or anything from a work repo without
  asking first. If a file looks sensitive, ask before uploading.
- Uploads go to the personal Cloudflare account, never Anduril infrastructure.
- Free tier: 10 GB stored, zero egress cost.
- Requires `wrangler` (`brew install cloudflare-wrangler2`).
