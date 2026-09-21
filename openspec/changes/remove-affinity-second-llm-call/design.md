# Design: Remove Affinity Second LLM Call

## Context

`backend/agents.py:229` calls `self.relationship_manager.analyze_and_update_affinity(...)` after every reply. That method in turn calls `self.analyzer_agent.run(prompt)` (a separate SimpleAgent + HelloAgentsLLM call) to get a semantic analysis. This is the second LLM call per chat.

The output of the analyzer is parsed into `{should_change, change_amount, reason, sentiment}` — roughly 4 fields. The same kind of signal is achievable with hand-tuned heuristics at zero latency.

## Approach

Add a new method `analyze_with_rules(player_message, npc_response, npc_name)` to `RelationshipManager` that produces the same `{change_amount, sentiment, reason}` dict. Switch the call site in `agents.py:229` to use the rules method by default, gated by `AFFINITY_MODE` env var.

The LLM path is kept as `analyze_with_llm` (renamed from `analyze_and_update_affinity`'s inner call) and accessible when `AFFINITY_MODE=llm`.

### Rule-based scoring algorithm

```python
def analyze_with_rules(self, player_message, npc_response, npc_name):
    text = player_message.lower()
    npc_role = NPC_ROLES.get(npc_name, {})

    # Persona-specific positive keywords (e.g., 张三 likes tech discussion)
    positive_kws = POSITIVE_BASE + npc_role.get('positive_keywords', [])
    negative_kws = NEGATIVE_BASE

    pos = sum(1 for kw in positive_kws if kw in text)
    neg = sum(1 for kw in negative_kws if kw in text)

    # Engagement multiplier from !, ?, length
    engagement = min(text.count('!') + text.count('?'), 3) * 0.5

    if pos > neg:
        change = min(2 + pos + int(engagement), 8)
        sentiment = 'positive'
        reason = '积极关键词 + ' + ('高参与度' if engagement > 1 else '普通回应')
    elif neg > pos:
        change = max(-(2 + neg), -6)
        sentiment = 'negative'
        reason = '消极关键词'
    else:
        change = 0
        sentiment = 'neutral'
        reason = '中性对话'

    return {
        'should_change': change != 0,
        'change_amount': float(change),
        'reason': reason,
        'sentiment': sentiment,
    }
```

The persona-specific positive_keywords live in `NPC_ROLES` (defined in `agents.py`), so adding a new NPC means adding their preferred keywords once.

### Mode switching

```python
class RelationshipManager:
    def __init__(self, llm):
        self.llm = llm
        self.mode = _os.getenv('AFFINITY_MODE', 'rules').lower()
        if self.mode not in ('rules', 'llm'):
            self.mode = 'rules'

    def analyze_and_update_affinity(self, npc_name, player_message, npc_response, player_id):
        if self.mode == 'rules':
            analysis = self.analyze_with_rules(player_message, npc_response, npc_name)
        else:
            analysis = self.analyze_with_llm(player_message, npc_response, npc_name)
        # ... rest unchanged: apply change, clamp to [0, 100], set, log
```

### Why not just remove the call entirely?

Removing the call would mean affinity never updates — that breaks the whole game mechanic. Rules keep the mechanic working at zero latency.

### Why keep the LLM path?

Two reasons:
1. **Debug mode**: dev/staging can flip `AFFINITY_MODE=llm` to compare heuristic vs semantic scoring side-by-side
2. **Future**: if a future feature needs deeper sentiment (e.g., sarcasm detection), the LLM path is the upgrade target

## Files

- `backend/relationship_manager.py`: add `analyze_with_rules`, rename inner LLM call to `analyze_with_llm`, gate on `mode`
- `backend/agents.py`: line 229 unchanged (still calls `analyze_and_update_affinity`); the implementation just picks rules vs llm internally
- `backend/.env.example`: add `AFFINITY_MODE=rules` line with comment

## Tradeoffs

| Aspect | Rules (new default) | LLM (old) |
|---|---|---|
| Latency | 0 ms | ~3 s |
| Cost | 0 tokens | ~600 tokens per chat |
| Accuracy on edge cases | weaker (sarcasm, irony) | better |
| Determinism | yes (same input → same output) | no (sampling) |
| Testability | trivially unit-testable | needs LLM mock |

## Verification

1. `backend/.env` has no `AFFINITY_MODE` → `mode == 'rules'` (verify in startup log)
2. Send 3 chats: praise, insult, neutral → check affinity log lines have correct sentiment and delta
3. Set `AFFINITY_MODE=llm` → restart → confirm `mode == 'llm'` and same scenarios produce roughly equivalent affinity changes (within ±2 points)
4. Confirm total chat latency dropped from ~5s to ~2s in backend logs
