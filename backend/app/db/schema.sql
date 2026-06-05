CREATE TABLE IF NOT EXISTS projects (
  project_id            TEXT PRIMARY KEY,
  name                  TEXT NOT NULL,
  status                TEXT NOT NULL,
  graph_id              TEXT,
  graph_build_task_id   TEXT,
  simulation_requirement TEXT,
  chunk_size            INTEGER DEFAULT 500,
  chunk_overlap         INTEGER DEFAULT 50,
  limits                TEXT,
  report_preferences    TEXT,
  total_text_length     INTEGER DEFAULT 0,
  archived              INTEGER DEFAULT 0,
  error                 TEXT,
  created_at            TEXT NOT NULL,
  updated_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS simulations (
  simulation_id   TEXT PRIMARY KEY,
  project_id      TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
  graph_id        TEXT,
  status          TEXT NOT NULL,
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
  status                 TEXT NOT NULL,
  title                  TEXT,
  summary                TEXT,
  simulation_requirement TEXT,
  preferences            TEXT,
  usage                  TEXT,
  error                  TEXT,
  created_at             TEXT NOT NULL,
  completed_at           TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
  task_id          TEXT PRIMARY KEY,
  task_type        TEXT NOT NULL,
  status           TEXT NOT NULL,
  progress         INTEGER DEFAULT 0,
  message          TEXT,
  result           TEXT,
  error            TEXT,
  metadata         TEXT,
  cancel_requested INTEGER DEFAULT 0,
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sims_project    ON simulations(project_id);
CREATE INDEX IF NOT EXISTS idx_reports_sim     ON reports(simulation_id);
CREATE INDEX IF NOT EXISTS idx_reports_project ON reports(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_type      ON tasks(task_type);
