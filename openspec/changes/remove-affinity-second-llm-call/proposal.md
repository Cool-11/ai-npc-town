# Proposal: Remove Affinity Second LLM Call

## Why

`backend/agents.py` calls the LLM **twice** per chat turn: once for the NPC reply (line 223), once for affinity analysis (line 229). The second call adds ~3 seconds to every reply but the affinity signal it produces is rough — keyword/emoji/sentiment heuristics can match ~80% of cases at zero latency. With first turn latency at ~5s end-to-end, cutting 3s gets us to ~2s which is interactive.

## What Changes

- `backend/relationship_manager.py`: add `analyze_with_rules(player_message, npc_response)` that returns `{should_change, change_amount, reason, sentiment}` based on heuristics (keywords, length, punctuation, NPC-specific persona multipliers)
- `backend/agents.py`: switch the chat path to use `analyze_with_rules`; keep `analyze_and_update_affinity` (LLM-based) as `analyze_with_llm` for opt-in debug mode
- No API/UI changes; behavior on the player side is identical (affinity still updates, can still be queried)
- New behavior is opt-in via `AFFINITY_MODE=rules|llm` env var, default `rules`
- **Breaking**: removed strict semantic analysis for very long multi-topic conversations (heuristics may miss nuanced context)

## Capabilities

### New Capabilities
- `affinity-system`: rule-based affinity scoring with deterministic output, no LLM dependency

### Modified Capabilities
(none — this is a performance optimization behind an existing capability)

## Impact

- **Files**: `backend/relationship_manager.py` (add rules), `backend/agents.py` (swap call), `backend/.env.example` (new var)
- **Latency**: chat reply goes from ~5s to ~2s (60% reduction)
- **Cost**: per-chat token usage drops ~40% (one full prompt completion)
- **Risk**: edge-case messages (long philosophical questions, sarcasm) may get less accurate affinity updates; mitigated by keeping LLM path as opt-in fallback
