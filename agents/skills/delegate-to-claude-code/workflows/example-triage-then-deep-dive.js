export const meta = {
  name: 'codex-authored-triage',
  description: 'Codex-authored workflow: classify each file, then deep-dive only the risky ones',
  whenToUse: 'When Codex owns the orchestration logic and Claude only executes it',
  phases: [
    { title: 'Triage', detail: 'cheap classification pass, one agent per file' },
    { title: 'Deep dive', detail: 'full audit, only for files triaged as risky' },
  ],
}

const FILES = args.files
const ROOT = args.root

const TRIAGE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['file', 'risk', 'reason'],
  properties: {
    file: { type: 'string' },
    risk: { type: 'string', enum: ['high', 'low'] },
    reason: { type: 'string' },
  },
}

const AUDIT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['file', 'worstDefect', 'exploitPath'],
  properties: {
    file: { type: 'string' },
    worstDefect: { type: 'string' },
    exploitPath: { type: 'string' },
  },
}

log(`Codex-authored script running over ${FILES.length} files`)

// Conditional fan-out: the deep dive is skipped entirely for low-risk files,
// so the branch decision is made by this script, not by any model's judgment.
const audited = await pipeline(
  FILES,
  (file) => agent(
    `Read ${ROOT}/target/${file}. Classify it as "high" risk if it contains a security-relevant defect (injection, weak crypto, auth bypass), otherwise "low". Set file to exactly "${file}".`,
    { label: `triage:${file}`, phase: 'Triage', schema: TRIAGE_SCHEMA, model: 'sonnet' }
  ),
  (triage, file) => {
    if (!triage || triage.risk !== 'high') {
      return { file, skipped: true, risk: triage ? triage.risk : 'unknown' }
    }
    return agent(
      `Read ${ROOT}/target/${file} and report only the single worst defect plus a concrete exploit path. Set file to exactly "${file}".`,
      { label: `audit:${file}`, phase: 'Deep dive', schema: AUDIT_SCHEMA, model: 'opus' }
    )
  }
)

const deepDived = audited.filter((r) => r && !r.skipped)
const skipped = audited.filter((r) => r && r.skipped)

log(`Deep dived ${deepDived.length}, skipped ${skipped.length}`)

return {
  authoredBy: 'codex',
  scriptWasVerbatim: true,
  deepDived,
  skipped,
  budgetRemaining: budget.remaining(),
}
