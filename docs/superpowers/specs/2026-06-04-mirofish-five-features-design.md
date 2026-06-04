# MiroFish Five-Feature Design Spec
**Date:** 2026-06-04  
**Approach:** C — All together, single delivery  
**Scope:** Backend + Frontend (Vue 3 + Flask)

---

## Overview

Five coordinated improvements to MiroFish:

1. **i18n** — Full app English/Chinese toggle via a custom composable
2. **Pre-run Limits** — Per-run caps on nodes, relations, personas, LLM calls set in the Home console
3. **Stop / Resume / Reset Report** — Cooperative cancellation + resume-from-checkpoint for report generation
4. **LLM Token / Cost Tracking** — Live counter during active runs + per-project summary on history cards
5. **Project Listing Fix** — Enrich the existing `HistoryDatabase` component with live status, usage data, and current-project visibility

All new UI is built bilingual from day one. No feature ships without its translations.

---

## 1. i18n Architecture

### Composable: `frontend/src/composables/useLocale.js`

```js
// Singleton reactive locale, persisted to localStorage
import { ref } from 'vue'
import zh from '../locales/zh.js'
import en from '../locales/en.js'

const MAPS = { zh, en }
const locale = ref(localStorage.getItem('mirofish_locale') || 'zh')

export function useLocale() {
  const t = (key) => MAPS[locale.value]?.[key] ?? key
  const setLocale = (lang) => {
    locale.value = lang
    localStorage.setItem('mirofish_locale', lang)
  }
  return { locale, t, setLocale }
}
```

### Translation files

- `frontend/src/locales/zh.js` — flat key-value object, all Chinese strings
- `frontend/src/locales/en.js` — same keys, English values
- Keys use dot-notation namespacing: `home.startEngine`, `report.stop`, `nav.github`, etc.

### Toggle button

Added to the navbar in `App.vue` — visible on every page via the router layout.

```html
<!-- in App.vue navbar -->
<button @click="setLocale(locale === 'zh' ? 'en' : 'zh')">
  {{ locale === 'zh' ? 'EN' : '中' }}
</button>
```

### Files touched for translation

All hardcoded Chinese strings replaced with `t('...')` calls:

`App.vue`, `Home.vue`, `HistoryDatabase.vue`, `Process.vue`, `MainView.vue`,  
`Step1GraphBuild.vue`, `Step2EnvSetup.vue`, `Step3Simulation.vue`, `Step4Report.vue`, `Step5Interaction.vue`,  
`SimulationRunView.vue`, `SimulationView.vue`, `ReportView.vue`, `InteractionView.vue`

---

## 2. Pre-run Limits

### Frontend — `Home.vue`

A collapsible "▸ Advanced Settings" toggle below the prompt textarea, inside the existing console box. Reveals 4 number inputs.

| Field | Label (EN) | Default | Min | Max |
|---|---|---|---|---|
| `max_nodes` | Max graph nodes | 500 | 50 | 5000 |
| `max_relations` | Max graph edges | 2000 | 100 | 20000 |
| `max_personas` | Max agents | 20 | 2 | 200 |
| `max_llm_calls` | Max LLM calls | 200 | 10 | 2000 |

Values are bundled into the existing `startSimulation()` payload alongside `simulationRequirement`.

### Backend

**`backend/app/models/project.py`**  
Add `limits: dict` field to the `Project` dataclass with the 4 keys above. Defaults to `{}` (no limits) for existing projects.

**`backend/app/api/graph.py`**  
Graph build pipeline reads `project.limits.get('max_nodes', None)` and `max_relations`. Stops node/edge extraction early when either limit is hit. Returns a `limits_hit` flag in the response so the frontend can inform the user.

**`backend/app/api/simulation.py`**  
Before starting OASIS, clamps the generated agent list to `limits.get('max_personas', None)`. If clamped, logs a warning.

**`backend/app/services/report_agent.py`**  
Initialises a `calls_remaining` counter from `limits.get('max_llm_calls', None)`. Decrements on every LLM call. When it hits zero, raises `BudgetExceededError`, which is caught by the orchestrator, saves completed sections, and sets status to `BUDGET_EXCEEDED`.

---

## 3. Stop / Resume / Reset Report

### Cancellation mechanism

`ReportManager` maintains a module-level dict:

```python
_cancellation_events: Dict[str, threading.Event] = {}
```

- `ReportManager.request_stop(report_id)` — sets the event
- `ReportManager.clear_stop(report_id)` — clears the event (used on resume/reset)
- `ReportAgent.generate_report()` checks `cancellation_event.is_set()` at the start of each section loop iteration; if set, saves progress and raises `CancellationError`

### New `ReportStatus` values

Add `CANCELLED` and `BUDGET_EXCEEDED` to the `ReportStatus` enum in `report_agent.py`.

### New API endpoints — `backend/app/api/report.py`

| Route | Method | Action |
|---|---|---|
| `/api/report/<report_id>/stop` | POST | Calls `ReportManager.request_stop(report_id)`. Returns `{success, message}`. |
| `/api/report/<report_id>/resume` | POST | Clears the cancellation event, determines last completed section index from `section_XX.md` files, restarts the background thread from that index. |
| `/api/report/<report_id>/reset` | POST | Clears stop flag, deletes all section files and report state, calls `generate_report` from scratch (`force_regenerate=True`). |

### Frontend — `Step4Report.vue`

Three action buttons shown conditionally:

| Button | Visible when | Action |
|---|---|---|
| Stop | `status == 'generating'` | `POST /api/report/<id>/stop` |
| Resume | `status == 'cancelled'` or `status == 'failed'` | `POST /api/report/<id>/resume` |
| Reset | `status != 'generating'` | Confirm dialog → `POST /api/report/<id>/reset` |

All button labels go through `t('report.stop')`, `t('report.resume')`, `t('report.reset')`.

---

## 4. LLM Token / Cost Tracking

### New file: `backend/app/services/usage_tracker.py`

```python
class UsageTracker:
    """Thread-safe per-project LLM usage accumulator."""

    RATE_TABLE = {
        # (input_$/1M, output_$/1M) by model name prefix
        'gpt-4o':        (5.00, 15.00),
        'gpt-4o-mini':   (0.15,  0.60),
        'qwen-plus':     (0.50,  1.50),
        'qwen-turbo':    (0.30,  0.90),
        'claude':        (3.00, 15.00),
    }
    DEFAULT_RATE = (1.00, 3.00)

    def record(self, project_id, prompt_tokens, completion_tokens, model_name): ...
    def get_usage(self, project_id) -> dict: ...  # totals + estimated_cost_usd
    def reset(self, project_id): ...
```

Persists to `uploads/usage/<project_id>.json`. Thread-safe with a per-project `threading.Lock`.

### `backend/app/utils/llm_client.py` changes

After every successful API call, extract `response.usage` and call:

```python
UsageTracker().record(
    project_id=self.project_id,   # new optional param on LLMClient.__init__
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
    model_name=self.model_name,
)
```

All call sites that instantiate `LLMClient` pass `project_id` through.

### New endpoint

`GET /api/usage/<project_id>` — returns:

```json
{
  "project_id": "...",
  "call_count": 42,
  "prompt_tokens": 18000,
  "completion_tokens": 6000,
  "total_tokens": 24000,
  "estimated_cost_usd": 0.14
}
```

### Frontend

**New `frontend/src/components/UsageCounter.vue`**  
Compact live bar: `Tokens: 24,000 | Est. cost: $0.14 | Calls: 42`  
Polls `GET /api/usage/<project_id>` every 3 seconds while a project is active. Stops polling on terminal status. Fully i18n-translated.

Injected into `Process.vue` — appears at the top of the active step panel.

**`HistoryDatabase.vue` card footer**  
Each project card gets a footer row showing `total_tokens` + `estimated_cost_usd` from the enriched list API (Section 5).

---

## 5. Project Listing Fix

### Backend — `GET /api/project/list`

Enrich the response payload per project:

```json
{
  "simulation_id": "...",
  "project_id": "...",
  "report_id": "...",
  "status": "building | simulating | reporting | done | failed | cancelled",
  "files": [...],
  "simulation_requirement": "...",
  "created_at": "...",
  "limits": { "max_nodes": 500, ... },
  "usage": {
    "total_tokens": 24000,
    "estimated_cost_usd": 0.14,
    "call_count": 42
  }
}
```

- Sorted by `created_at` descending (newest first, including in-progress)
- No status filter — all projects returned regardless of state

### Frontend — `HistoryDatabase.vue`

- **Active project** shown at top with a pulsing status badge (`Building graph…` / `Running simulation…` / `Generating report…`) driven by `status`
- **Card footer** shows `usage.total_tokens` + `usage.estimated_cost_usd` (from Section 4)
- **Navigation on click** routes to the correct step in `Process.vue` based on `status`, not always to step 1
- **Empty state** — if no projects yet, shows a translated call-to-action instead of a blank section
- **Polling** — polls `/api/project/list` every 5 seconds while any project has a non-terminal status; stops when all are terminal

All new text strings go through `t('history.*')`.

---

## Data Flow Summary

```
Home.vue (limits + prompt + files)
  → POST /api/simulation/start  { limits, requirement, files }
      → ProjectManager.create(limits)
      → LLMClient(project_id=...)  →  UsageTracker.record(...)
      → graph build  checks limits.max_nodes / max_relations
      → simulation   clamps to limits.max_personas
      → report_agent checks limits.max_llm_calls, checks cancellation_event

Process.vue
  → UsageCounter polls GET /api/usage/<project_id> every 3s

Step4Report.vue
  → Stop/Resume/Reset → POST /api/report/<id>/stop|resume|reset

Home.vue / HistoryDatabase.vue
  → polls GET /api/project/list every 5s (enriched with usage + status)
```

---

## Error Handling

| Scenario | Backend behaviour | Frontend behaviour |
|---|---|---|
| Limit hit during graph build | Returns `limits_hit: true` in response | Step 1 shows a yellow warning banner |
| `BudgetExceededError` in report agent | Status → `BUDGET_EXCEEDED`, completed sections saved | Resume button shown; partial report rendered |
| Stop requested mid-section | Current LLM call completes, then stops cleanly | Stop button replaced by Resume + Reset |
| Resume with no completed sections | Treated as a fresh generate | UI shows "Starting from beginning" |
| Usage JSON write fails | Log error, continue without tracking | Counter shows `—` |

---

## File Inventory

### New files
- `frontend/src/composables/useLocale.js`
- `frontend/src/locales/zh.js`
- `frontend/src/locales/en.js`
- `frontend/src/components/UsageCounter.vue`
- `backend/app/services/usage_tracker.py`

### Modified files
- `frontend/src/App.vue` — language toggle in navbar
- `frontend/src/views/Home.vue` — limits panel + i18n
- `frontend/src/components/HistoryDatabase.vue` — enriched cards + polling + i18n
- `frontend/src/views/Process.vue` — UsageCounter injection + i18n
- `frontend/src/components/Step4Report.vue` — stop/resume/reset buttons + i18n
- All other 9 Vue files listed in Section 1 — i18n strings only
- `backend/app/models/project.py` — `limits` field
- `backend/app/utils/llm_client.py` — usage tracking hook
- `backend/app/services/report_agent.py` — cancellation check + budget check
- `backend/app/api/report.py` — 3 new routes
- `backend/app/api/graph.py` — limits enforcement
- `backend/app/api/simulation.py` — persona clamping
- `backend/app/config.py` — rate table defaults

---

## Out of Scope

- Persistent user accounts or per-user settings
- Real-time streaming (SSE) for usage — polling is sufficient
- More than 2 languages
- Resuming simulation (not just report) from a checkpoint
