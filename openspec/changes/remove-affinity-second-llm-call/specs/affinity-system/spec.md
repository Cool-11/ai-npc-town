# Capability: affinity-system (delta)

This is a delta spec for the existing `affinity-system` capability introduced in baseline. It documents the new behavior being added by change `remove-affinity-second-llm-call`.

## ADDED Requirements

### Requirement: Mode-switchable scoring backend

The system SHALL support two scoring backends selected by `AFFINITY_MODE` env var:

- `rules` (default): rule-based heuristic scoring, no LLM call
- `llm`: original LLM-based semantic scoring (kept for opt-in debug)

Switching modes SHALL NOT change the `affinity` value range, the `level` thresholds, or the persistence format.

#### Scenario: rules mode is default

- Given `.env` has no `AFFINITY_MODE` line (or `AFFINITY_MODE=rules`)
- When the backend starts
- Then `RelationshipManager.mode == "rules"`

#### Scenario: opt back into LLM mode

- Given `.env` has `AFFINITY_MODE=llm`
- When the backend starts
- Then `RelationshipManager.mode == "llm"`
- And each chat turn invokes `analyze_with_llm` instead of `analyze_with_rules`

### Requirement: Rule-based scoring (rules mode)

When `mode == "rules"`, the system SHALL compute `change_amount` and `sentiment` from the player message and NPC reply without invoking any LLM.

Inputs considered:
- Lexicon of positive/negative keywords (configurable list per NPC persona)
- Message length (very short messages get +0)
- Punctuation density (`!` `?` count as engagement)
- NPC-specific multipliers (e.g., 张三 weights technical words positively)

#### Scenario: positive sentiment from praise keyword

- Given player message contains "好厉害" or "thanks"
- When the rule scorer runs
- Then `sentiment == "positive"` and `change_amount in [3, 7]`

#### Scenario: negative sentiment from hostile keyword

- Given player message contains "笨" or "stupid"
- When the rule scorer runs
- Then `sentiment == "negative"` and `change_amount in [-5, -2]`

#### Scenario: neutral message

- Given player message has no sentiment triggers
- When the rule scorer runs
- Then `sentiment == "neutral"` and `change_amount == 0`

### Requirement: Backward-compatible API

The public method `analyze_and_update_affinity(npc_name, player_message, npc_response, player_id)` SHALL continue to exist and return the same dict shape `{changed, affinity, level, modifier, change_amount, sentiment, reason}`.

#### Scenario: rules mode call returns same shape

- Given `mode == "rules"`
- When `analyze_and_update_affinity` is called
- Then return value has the same keys as the LLM-mode implementation

### Requirement: Logging parity

The system SHALL emit log lines with the same format in both modes:
- `[INFO] 好感度变化: 50.0 -> 55.0 (+5.0)`
- `[INFO]   原因: <reason>`
- `[INFO]   情感: <sentiment>`

#### Scenario: rules mode log lines match LLM mode format

- Given `mode == "rules"` and an update occurs
- When the log line is emitted
- Then it contains 好感度变化, 原因, and 情感 substrings