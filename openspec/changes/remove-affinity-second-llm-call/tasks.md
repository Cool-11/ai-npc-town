# Tasks: Remove Affinity Second LLM Call

## 1. Add rule-based scoring method

- [ ] 1.1 In `backend/relationship_manager.py`, define module-level `POSITIVE_BASE`, `NEGATIVE_BASE` keyword lists
- [ ] 1.2 Add `NPC_POSITIVE_KEYWORDS` dict mapping npc_name → extra positive keywords (extend `NPC_ROLES` in `agents.py`)
- [ ] 1.3 Implement `analyze_with_rules(player_message, npc_response, npc_name) -> Dict` returning `{should_change, change_amount, reason, sentiment}`

## 2. Rename existing LLM call and add mode switch

- [ ] 2.1 Rename inner `analyzer_agent.run(prompt)` block to `analyze_with_llm(...)` method (keeps LLM call, no behavior change)
- [ ] 2.2 Refactor `analyze_and_update_affinity` to read `self.mode` from env at init and dispatch to rules vs llm
- [ ] 2.3 Add `mode` attribute to `RelationshipManager.__init__`, defaulting to `rules`

## 3. Update NPC role definitions

- [ ] 3.1 In `backend/agents.py` `NPC_ROLES`, add `positive_keywords: [...]` per NPC (张三: ["技术", "框架", "算法"]; 李四: ["需求", "产品"]; 王五: ["设计", "界面", "配色"])

## 4. Env example

- [ ] 4.1 Add `AFFINITY_MODE=rules` to `backend/.env.example` with comment explaining the two modes

## 5. Verification

- [ ] 5.1 Start backend, confirm log line shows `mode: rules`
- [ ] 5.2 Send 3 test messages via curl to `/chat`, check dialogue log for correct affinity changes
- [ ] 5.3 Set `AFFINITY_MODE=llm` in `.env`, restart, re-send same 3 messages, confirm affinity delta is roughly equivalent
- [ ] 5.4 Time a chat round-trip; expect ~2s (down from ~5s)

## 6. Commit + PR

- [ ] 6.1 `git add -A` (include `openspec/changes/remove-affinity-second-llm-call/`)
- [ ] 6.2 `git commit -m "perf(backend): affinity scoring in rules mode (no LLM call)"`
- [ ] 6.3 Push branch, open PR titled `perf: affinity rule-based scoring (cuts chat latency 60%)`
