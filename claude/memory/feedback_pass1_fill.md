---
name: Always Run Pass 1 Fill Script
description: Must run fill-form.js (Pass 1) before any manual field filling — it handles 70% of fields automatically
type: feedback
---

When filling job application forms, ALWAYS run fill-form.js (Pass 1) first before doing any manual filling.

**Why:** During the March 2026 Anthropic applications, Pass 1 was skipped entirely — not because the skill said to skip it, but because Claude improvised manual filling instead of following the documented SKILL.md workflow. All fields were filled manually via individual MCP calls (fill, click-snapshot-click for dropdowns), which was extremely slow (~35 MCP round trips per form). The fill-form.js script with profile.json + greenhouse.json selectors handles ~70% of standard fields in a single JS injection. Lesson: when a skill has a documented workflow, follow it — don't improvise.

**How to apply:** The correct flow is:
1. Navigate to job URL
2. Read fill-form.js, replace $$PROFILE$$ with profile.json, $$ATS_CONFIG$$ with selectors/greenhouse.json
3. Inject via evaluate_script (1 MCP call → fills most fields)
4. Upload resume via MCP upload_file
5. Run extract-form.js to see what's left unfilled
6. Claude decides answers + bulk-fill.js for remaining custom fields
