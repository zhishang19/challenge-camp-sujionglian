# Phase 2 Generated Data Consolidation Report

## Input: generated/ (--records-per-day 10000)

| Day | File | Raw | Cleaned | Dropped |
|-----|------|:---:|:---:|:---:|
| D02 | tool_result.jsonl | 3000 | 3000 | 0 |
| D02 | user_behavior.jsonl | 7000 | 6770 | 230 |
| D03 | chat_sessions_dirty.csv | 11038 | 9348 | 1690 |
| D04 | chat_logs_raw.jsonl | 4000 | 3863 | 137 |
| D04 | knowledge_raw.jsonl | 1500 | 1500 | 0 |
| D04 | preferences_raw.csv | 2789 | 1923 | 866 |
| D04 | tool_result_raw.jsonl | 2000 | 1964 | 36 |
| D05 | memory_events_raw.jsonl | 6000 | 5799 | 201 |
| D05 | user_memory_snapshots_raw.csv | 3320 | 2038 | 1282 |
| D05 | conflict_candidates_raw.csv | 1230 | 1000 | 0 |
| D06 | eval_prompts_dirty.csv + trace | 5488 | 5000 | 0 |

## Cleaning Rules Applied

| Rule | Description |
|------|-------------|
| Filler words | 嗯, 啊, 呃, 那个, 就是 — removed from leading position |
| Symbol removal | 【】, @@@, ** — content preserved, wrapper stripped |
| Noise markers | [ASR], [draft], #todo, <!--cached-->, ENDEND, <<<>>>> |
| HTML tags | <p>, </p> — removed |
| Typos | 奇麟→麒麟, 其麟→麒麟, 设制→设置, 知只→知识, 会义→会议 |
| PII redaction | email → [REDACTED], phone → [REDACTED] |
| Dedup | Duplicate records removed |
| Time normalization | Multiple formats → YYYY-MM-DD HH:MM:SS |
| UID normalization | Uppercase, missing → UNKNOWN |
| Filler dedup | 然后然后 → 然后 |

## Output Files

| File | Records |
|------|:---:|
| tool_result_d02.json | 3000 |
| user_behavior_clean.json | 6770 |
| chat_sessions_clean.json | 9348 |
| chat_turns.json | 3863 |
| knowledge_items.json | 1500 |
| preferences.json | 1923 |
| tool_executions.json | 1964 |
| memory_events.json | 5799 |
| memory_snapshots_resolved.json | 2038 |
| conflict_resolution_v5.json | 1000 |
| quality_evaluation.json | 5000 |
