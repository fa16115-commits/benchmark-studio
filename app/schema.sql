PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT, role TEXT NOT NULL, initials TEXT
);

CREATE TABLE IF NOT EXISTS engagements (
  id INTEGER PRIMARY KEY, code TEXT UNIQUE, title TEXT NOT NULL, client TEXT, sector TEXT,
  objective TEXT, context TEXT, decision_statement TEXT, expected_outcomes TEXT,
  scope TEXT DEFAULT '{}', current_stage INTEGER DEFAULT 0, status TEXT DEFAULT 'active',
  lead_id INTEGER REFERENCES users(id), storyline TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS gates (
  id INTEGER PRIMARY KEY, engagement_id INTEGER REFERENCES engagements(id) ON DELETE CASCADE,
  stage INTEGER, status TEXT DEFAULT 'locked',
  submitted_by INTEGER, submitted_at TEXT, decided_by INTEGER, decided_at TEXT, comment TEXT,
  cosigned_by INTEGER, UNIQUE(engagement_id, stage)
);

CREATE TABLE IF NOT EXISTS dimensions (
  id INTEGER PRIMARY KEY, engagement_id INTEGER REFERENCES engagements(id) ON DELETE CASCADE,
  name TEXT, description TEXT, weight REAL DEFAULT 3, sort INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS criteria (
  id INTEGER PRIMARY KEY, engagement_id INTEGER REFERENCES engagements(id) ON DELETE CASCADE,
  dimension_id INTEGER REFERENCES dimensions(id) ON DELETE CASCADE,
  name TEXT, description TEXT, assessment_type TEXT DEFAULT 'rating', weight REAL DEFAULT 3,
  direction TEXT DEFAULT 'higher_better', unit TEXT, relevance TEXT, researchability TEXT,
  comparability TEXT, evidence_risk TEXT, status TEXT DEFAULT 'proposed', sort INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS questions (
  id INTEGER PRIMARY KEY, engagement_id INTEGER REFERENCES engagements(id) ON DELETE CASCADE,
  criterion_id INTEGER REFERENCES criteria(id) ON DELETE CASCADE,
  text TEXT, indicator TEXT, guidance TEXT
);

CREATE TABLE IF NOT EXISTS comparators (
  id INTEGER PRIMARY KEY, engagement_id INTEGER REFERENCES engagements(id) ON DELETE CASCADE,
  name TEXT, kind TEXT, region TEXT, rationale TEXT, evidence_note TEXT, status TEXT DEFAULT 'proposed'
);

CREATE TABLE IF NOT EXISTS research_tasks (
  id INTEGER PRIMARY KEY, engagement_id INTEGER REFERENCES engagements(id) ON DELETE CASCADE,
  comparator_id INTEGER REFERENCES comparators(id) ON DELETE CASCADE,
  question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'not_started', sufficiency TEXT, draft_response TEXT,
  rating REAL, checklist TEXT, value REAL, value_unit TEXT,
  comparability TEXT DEFAULT '{}', notable TEXT, run_log TEXT, error TEXT,
  updated_at TEXT DEFAULT (datetime('now')),
  UNIQUE(comparator_id, question_id)
);

CREATE TABLE IF NOT EXISTS evidence (
  id INTEGER PRIMARY KEY, code TEXT, engagement_id INTEGER REFERENCES engagements(id) ON DELETE CASCADE,
  task_id INTEGER REFERENCES research_tasks(id) ON DELETE CASCADE,
  claim TEXT, summary TEXT, snapshot TEXT, publisher TEXT, title TEXT, pub_date TEXT, url TEXT,
  locator TEXT, source_category TEXT, priority TEXT, accessibility TEXT, limitations TEXT,
  accessed_at TEXT DEFAULT (date('now')), status TEXT DEFAULT 'pending',
  reviewed_by INTEGER, reviewed_at TEXT, review_comment TEXT, validation TEXT
);

CREATE TABLE IF NOT EXISTS search_log (
  id INTEGER PRIMARY KEY, task_id INTEGER REFERENCES research_tasks(id) ON DELETE CASCADE,
  query TEXT, created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS content_items (
  id INTEGER PRIMARY KEY, engagement_id INTEGER REFERENCES engagements(id) ON DELETE CASCADE,
  section TEXT, content_type TEXT, comparator_id INTEGER, title TEXT, text TEXT,
  evidence_ids TEXT DEFAULT '[]', assumptions TEXT, status TEXT DEFAULT 'pending',
  ai_original TEXT, version INTEGER DEFAULT 1, created_by TEXT DEFAULT 'AI',
  reviewed_by INTEGER, reviewed_at TEXT, in_deliverable INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY, engagement_id INTEGER, entity_type TEXT, entity_id INTEGER, kind TEXT,
  before TEXT, after TEXT, reason TEXT, user_id INTEGER, created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS qa_issues (
  id INTEGER PRIMARY KEY, engagement_id INTEGER REFERENCES engagements(id) ON DELETE CASCADE,
  rule TEXT, severity TEXT, entity_type TEXT, entity_id INTEGER, message TEXT,
  status TEXT DEFAULT 'open', source TEXT DEFAULT 'rules', created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS source_rules (
  id INTEGER PRIMARY KEY, priority TEXT, category TEXT, examples TEXT, preferred_for TEXT,
  treatment TEXT, key_rule TEXT, sort INTEGER
);

CREATE TABLE IF NOT EXISTS prompts (
  key TEXT PRIMARY KEY, stage INTEGER, title TEXT, body TEXT, version INTEGER DEFAULT 1,
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY, engagement_id INTEGER, kind TEXT, status TEXT DEFAULT 'queued',
  progress INTEGER DEFAULT 0, total INTEGER DEFAULT 0, message TEXT,
  created_at TEXT DEFAULT (datetime('now')), finished_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY, user_id INTEGER, engagement_id INTEGER, action TEXT, detail TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
