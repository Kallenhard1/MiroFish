# Report Persistence & Control — Design Spec

**Date:** 2026-06-05
**Status:** Approved (design); pending implementation plan
**Scope:** MiroFish only

## 1. Problem & Goals

MiroFish is a 5-step workflow (Graph Build → Environment Setup → Simulation → Report → Deep Interaction). Today all state is persisted as **JSON/section files on disk** via static-method "Manager" classes (`ProjectManager`, `SimulationManager`, `ReportManager`). The exception is `TaskManager`, which is an **in-memory singleton** (`self._tasks = {}`) — so every in-flight task (graph build, report generation) is **lost on backend restart**, even though the underlying report sections/files survive. This is the root cause of "I have to build/request again."

Goals:

1. **Durable persistence + step recovery** — return to any completed 5/5 step without rebuilding or re-requesting. Achieved via a SQLite index layer that also owns task state.
2. **Report preferences modal** — control budget, tools, section structure, language, and a Quick/Deep/Custom mode before running a report.
3. **Cancellation & management** — cancel report generation, graph build, and simulation runs; delete a whole project; rename/archive projects.
4. **Usage on the report view** — show token/cost/call usage on the report view (project-cumulative + per-report).

Non-goals: multi-user/Postgres, ORM/migrations framework, moving bulky content out of files.

## 2. Architectural Decision

**Hybrid: files remain authoritative for content; SQLite is a queryable index + control plane.**

- DB choice: **SQLite via Python stdlib `sqlite3`** (Approach A — no new dependencies). Justified by the single-process, threaded, file-based design. Postgres/ORM deferred until/if multi-user.
- DB is **authoritative for status/metadata**; files stay **authoritative for content** (report sections, outline markdown, profiles, extracted text, ontology JSON).
- The DB is **disposable**: it is fully reconstructable from the files via a rebuild script, which is why no migration framework is required.

### Concurrency model (the decisive constraint)

The backend spawns `threading.Thread(daemon=True)` for every build/report; those threads write progress constantly. Per Python `sqlite3` rules, **one connection per thread**; per SQLite, **WAL mode = many readers + one writer** (journal mode is orthogonal to threading mode).

`app/db/connection.py`:

```python
import sqlite3, threading
from ..config import Config

_local = threading.local()   # one connection per thread (hard rule)

def get_conn():
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(Config.DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")    # many readers + 1 writer
        conn.execute("PRAGMA busy_timeout=30000;")  # writer waits, doesn't error
        conn.execute("PRAGMA foreign_keys=ON;")     # ON DELETE CASCADE
        _local.conn = conn
    return conn
```

Each background thread calls `get_conn()` inside its own thread → its own connection; no cross-thread sharing, no `check_same_thread=False` hack. WAL + `busy_timeout` make concurrent progress writes queue politely instead of raising `database is locked`.

Sources informing this: <https://sqlite.org/threadsafe.html>, <https://ricardoanderegg.com/posts/python-sqlite-thread-safety/>, <https://flask.palletsprojects.com/en/stable/patterns/sqlite3/>.

## 3. Data Model (`app/db/schema.sql`, idempotent)

```sql
CREATE TABLE IF NOT EXISTS projects (
  project_id            TEXT PRIMARY KEY,
  name                  TEXT NOT NULL,
  status                TEXT NOT NULL,          -- ProjectStatus
  graph_id              TEXT,
  graph_build_task_id   TEXT,
  simulation_requirement TEXT,
  chunk_size            INTEGER DEFAULT 500,
  chunk_overlap         INTEGER DEFAULT 50,
  limits                TEXT,                   -- JSON (budget caps)
  report_preferences    TEXT,                   -- JSON: last-used modal defaults
  total_text_length     INTEGER DEFAULT 0,
  archived              INTEGER DEFAULT 0,      -- rename/archive feature
  error                 TEXT,
  created_at            TEXT NOT NULL,
  updated_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS simulations (
  simulation_id   TEXT PRIMARY KEY,
  project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
  graph_id        TEXT,
  status          TEXT NOT NULL,                -- SimulationStatus
  enable_twitter  INTEGER DEFAULT 1,
  enable_reddit   INTEGER DEFAULT 1,
  entities_count  INTEGER DEFAULT 0,
  profiles_count  INTEGER DEFAULT 0,
  current_round   INTEGER DEFAULT 0,
  total_rounds    INTEGER DEFAULT 0,
  config_generated INTEGER DEFAULT 0,
  error           TEXT,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
  report_id              TEXT PRIMARY KEY,
  simulation_id          TEXT REFERENCES simulations(simulation_id) ON DELETE CASCADE,
  project_id             TEXT REFERENCES projects(project_id) ON DELETE CASCADE,
  graph_id               TEXT,
  status                 TEXT NOT NULL,         -- ReportStatus
  title                  TEXT,
  summary                TEXT,
  simulation_requirement TEXT,
  preferences            TEXT,                  -- JSON snapshot of settings used for THIS report
  usage                  TEXT,                  -- JSON snapshot: per-report token/cost/call delta
  error                  TEXT,
  created_at             TEXT NOT NULL,
  completed_at           TEXT
);

-- Durability fix: tasks move from in-memory dict -> table. Also the universal cancel point.
CREATE TABLE IF NOT EXISTS tasks (
  task_id          TEXT PRIMARY KEY,
  task_type        TEXT NOT NULL,               -- graph_build | report_generate | report_resume | report_reset | ...
  status           TEXT NOT NULL,               -- TaskStatus
  progress         INTEGER DEFAULT 0,
  message          TEXT,
  result           TEXT,                          -- JSON
  error            TEXT,
  metadata         TEXT,                          -- JSON (project_id, report_id, ...)
  cancel_requested INTEGER DEFAULT 0,            -- cooperative cancel flag (polled by worker)
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sims_project    ON simulations(project_id);
CREATE INDEX IF NOT EXISTS idx_reports_sim     ON reports(simulation_id);
CREATE INDEX IF NOT EXISTS idx_reports_project ON reports(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_type      ON tasks(task_type);
```

Design choices:

- **DB authoritative for status/metadata; files for content.** Managers write both together; "list/status" reads come from one indexed query instead of directory scans.
- **`tasks` is the universal cancellation point.** `cancel_requested` works for report generation, graph builds, and simulations; each worker polls its own row. Replaces the in-memory `threading.Event` with something that survives restart and is UI-readable. (The same-process `threading.Event` may be retained for fast liveness, but `cancel_requested` is the durable source of truth.)
- **Preferences in two places by intent:** `projects.report_preferences` = last-used defaults (modal pre-fills); `reports.preferences` = immutable snapshot of what THIS report ran with (self-describing reports).
- **`reports.usage`** = per-report token/cost/call delta snapshot.

## 4. Repository Seam

Keep Manager public method signatures identical; swap internals to write files (content) + DB (index).

New files:

```
backend/app/db/
  __init__.py
  connection.py     # get_conn() (above)
  schema.sql        # section 3
  bootstrap.py      # init_db(app): schema -> reconcile -> recover orphaned tasks
backend/app/repositories/
  __init__.py
  project_repo.py    # CRUD on projects
  simulation_repo.py
  report_repo.py
  task_repo.py
```

Example seam — `ReportManager.save_report()` keeps its signature:

```python
@classmethod
def save_report(cls, report: Report) -> None:
    cls._write_report_files(report)   # content -> files (unchanged)
    report_repo.upsert(report)        # status/metadata -> DB index (new)
```

`TaskManager` is the one behavior change (in-memory → DB-backed) but keeps identical method signatures (`create_task`, `update_task`, `get_task`, `complete_task`, `fail_task`), so `report.py`'s closures and frontend polling are untouched.

Encapsulation rationale: every consumer already talks to data through a Manager method (e.g. `report.py` calls `ReportManager.get_report(id)`, never `open(meta.json)`), so the storage backend is fully swappable behind the seam. The one frontend exception, `HistoryDatabase.vue` → `/api/graph/project/list`, is repointed at the new indexed query.

`ON DELETE CASCADE` + `PRAGMA foreign_keys=ON` makes "delete project" a single-row delete that cleans simulations and reports from the index; a file-cleanup pass removes on-disk folders.

## 5. Preferences Flow & Modal

Preferences object (stored in `reports.preferences` and `projects.report_preferences`):

```jsonc
{
  "mode": "quick" | "deep" | "custom",
  "max_llm_calls": 50,
  "tools": ["insight_forge", "panorama_search", "quick_search", "interview_agents"],
  "min_sections": 2,
  "max_sections": 5,
  "min_tool_calls": 3,
  "max_tool_calls": 5,
  "language": "auto" | "en" | "zh"
}
```

Mode presets fill the other fields; Custom unlocks them:

| Field | Quick | Deep | Custom |
|---|---|---|---|
| sections | 2–3 | 4–5 | user |
| tools | insight_forge, quick_search | all 4 | user |
| tool calls/section | 1–2 | 3–5 | user |
| max_llm_calls | low | high | user |

`interview_agents` is **excluded from Quick by default** (needs OASIS running); available in Custom.

Flow:

1. New `frontend/src/components/ReportPreferencesModal.vue`, opened by "Generate Report" in `Step4Report.vue`.
2. On open → `GET /api/report/preferences/<project_id>` returns last-used defaults (first time → Deep defaults, matching current behavior).
3. On confirm → existing `POST /api/report/generate` gains a `preferences` field.
4. `report.py`: passes prefs to `ReportAgent(preferences=...)`, snapshots into `reports.preferences`, saves as project's new `report_preferences` defaults.

Backend wiring into `ReportAgent` (turns buried constants into explicit inputs):

| Preference | Today | Change |
|---|---|---|
| `max_llm_calls` | `limits.get('max_llm_calls')` → `_calls_remaining` | already wired |
| `tools` | `_define_tools()` returns all 4; `VALID_TOOL_NAMES` const | filter both by `preferences["tools"]` |
| `min/max_sections` | hardcoded "2–5" in `PLAN_SYSTEM_PROMPT` | inject numbers into plan prompt |
| `min/max_tool_calls` | class consts `MAX_TOOL_CALLS_PER_SECTION=5`, local `min_tool_calls=3` | read from preferences per instance |
| `language` | inferred from requirement text | explicit language directive in section prompts when not `auto` |

## 6. Cancellation, Management & Usage

### Cancellation — unified at the `tasks` table

Each worker polls its own `tasks.cancel_requested` at safe checkpoints.

| Target | Backend today | Work needed |
|---|---|---|
| Report generation | `/stop`,`/resume`,`/reset` + `threading.Event` | also set `tasks.cancel_requested`; UI Stop/Resume/Reset in `Step4Report.vue`/`ReportView.vue` |
| Simulation run | `SimulationRunner.stop_simulation()` + `POST /api/simulation/stop` + IPC | UI Stop button in `Step3Simulation.vue` |
| Graph build | none | NEW: pass `cancel_check` closure into `add_text_batches()` + `_wait_for_episodes()`; poll between batches → task `cancelled`, project → `failed`/`ontology_generated`; endpoint `POST /api/graph/build/<task_id>/cancel` |

### Project management

- `DELETE /api/graph/project/<id>` — extend existing: DB cascade (FKs clean sims+reports rows) + remove on-disk folders (`projects/`, related `simulations/`, `reports/`) + usage file + optionally the Zep graph. Refuses or force-cancels if a task is mid-flight.
- `PATCH /api/graph/project/<id>` — `{ "name": "...", "archived": true|false }`. `archived=1` rows drop out of default `/project/list` (add `?include_archived=1` + an "Archived" toggle in `HistoryDatabase.vue`).

### Usage on the report view

1. **Cheap:** drop existing `<UsageCounter :projectId="report.project_id" />` into `ReportView.vue` (project-cumulative, live-polling, zero new backend).
2. **Per-report (self-describing):** `reports.usage` JSON column. At report start, snapshot project usage counters as a baseline; at terminal state, store the delta (tokens/calls/cost for THIS report). Report view shows both "this report cost X" and "project total Y", paired with the preferences snapshot. Uses the baseline-delta trick so `report_id` need not be threaded through every LLM call.

## 7. Disposable DB: rebuild, startup wiring & crash recovery

App startup (`backend/app/__init__.py` `create_app()`):

```python
from .db.bootstrap import init_db
init_db(app)   # 1) run schema.sql (idempotent)  2) reconcile  3) recover orphaned tasks
```

1. **`rebuild_index.py` — DB is disposable.** Scans authoritative files and upserts rows (also invoked by `init_db` when the DB is empty/new):

   ```
   uploads/projects/*/project.json     -> projects
   uploads/simulations/*/state.json    -> simulations
   uploads/reports/*/meta.json (+ outline.json) -> reports
   uploads/usage/*.json                -> left file-based, read on demand
   ```

   Delete `mirofish.db`, restart, and the index is reconstructed.

2. **Reconcile** — on each startup, re-scan files to confirm the index matches (covers a report that finished exactly when a DB write crashed). Full boot re-scan is acceptable for single-user scale.

3. **Crash recovery (durability payoff).** On startup, find tasks left in `processing` (their threads died with the process) and resolve honestly:

   | Orphaned task | Resolution |
   |---|---|
   | `report_generate` / `report_resume` | task → `failed` ("interrupted by restart"); on-disk sections survive → user sees **Resume** (existing `/resume` continues from last completed section) |
   | `graph_build` | task → `failed`; project → `failed` with clear message → user can force-rebuild |

   This lets the app distinguish "still running" from "died mid-run" after a restart and route the latter to the Resume path instead of forcing a rebuild.

   > **Pre-existing quirk to fix during implementation:** `api/graph.py` currently calls `task_manager.create_task(f"Build graph: {graph_name}")` — passing a human description into the `task_type` slot. Crash-recovery and the `idx_tasks_type` index assume `task_type` is a stable machine value (`graph_build`). Normalize this to `create_task("graph_build", metadata={"label": "Build graph: ...", "project_id": ...})` so recovery can match by type.

## 8. Config additions

- `Config.DB_PATH` = `os.path.join(Config.UPLOAD_FOLDER, 'mirofish.db')`.

## 9. Affected files (summary)

Backend (new): `app/db/{connection,bootstrap,schema.sql}.py`, `app/repositories/{project,simulation,report,task}_repo.py`, `app/db/rebuild_index.py`.
Backend (modified): `models/task.py` (DB-backed), `models/project.py`, `services/simulation_manager.py`, `services/report_agent.py` (ReportManager seam + `ReportAgent` preferences + per-report usage), `services/graph_builder.py` (cancel_check), `api/graph.py` (cancel build, PATCH project, delete cascade, list via index), `api/report.py` (preferences in generate, preferences GET, durable cancel), `app/__init__.py` (init_db), `config.py` (DB_PATH).
Frontend (new): `components/ReportPreferencesModal.vue`.
Frontend (modified): `components/Step3Simulation.vue` (stop), `components/Step4Report.vue` (prefs modal + stop/resume/reset), `views/ReportView.vue` (UsageCounter + per-report usage + controls), `components/HistoryDatabase.vue` (archive toggle, delete/rename actions), `api/{report,graph,simulation}.js` (new endpoints).
