# People's Priorities AI — Copilot Context (Backend API Service)

> This file is automatically read by GitHub Copilot to understand the project context.
> **DO NOT DELETE** — It ensures every team member gets full context in Copilot Chat.

---

## PROJECT OVERVIEW

**People's Priorities AI** is a multilingual AI platform for constituency development planning under India's MPLADS scheme (₹5 Crore/year per MP). It converts unstructured citizen complaints (text/audio/image in 13 Indian languages) into transparent, data-driven MP funding recommendations.

### Core Problem
No systematic way for MPs to collect citizen demands → funds misallocated, unheard voices, no accountability. This platform is the missing decision-support layer.

### Team & Scope
- Team of 3, hackathon prototype
- Demo constituency: Jagatsinghpur, Odisha
- Languages: English + Hindi + Odia (13 total in UI)

---

## ARCHITECTURE (6 Layers)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PEOPLE'S PRIORITIES AI                            │
├─────────────┬───────────────────────────────────────┬───────────────┤
│  FRONTEND   │          BACKEND SERVICES              │   DATABASE   │
│  (React)    │                                        │   (MySQL)    │
│             │  ┌──────────────┐  ┌────────────────┐  │              │
│  Layer 1 ──►│  │ backend-api  │  │  scheduler     │  │  19 tables   │
│  Layer 6 ──►│  │ (FastAPI)    │  │  (Layers 2-5)  │  │  7 triggers  │
│             │  │ Port: 8000   │  │  23:30 nightly  │  │  6 views     │
│  Port: 5173 │  └──────────────┘  └────────────────┘  │  Port: 3306  │
└─────────────┴───────────────────────────────────────┴───────────────┘
```

### Three Repos
1. **`coz_code_backend`** (THIS REPO) — FastAPI backend for Layer 1 (citizen intake) + Layer 6 (MP dashboard). Always running on port 8000.
2. **`coz_code_scheduler`** — Python scheduler for Layers 2-5. Runs nightly at 23:30 or manually triggered.
3. **`coz_code_frontend`** — React + Vite UI on port 5173. Citizen submission + dashboards.

---

## THIS REPO: BACKEND API (`coz_code_backend`)

### Tech Stack
- **Framework:** FastAPI (Python)
- **Database:** MySQL 8.0.13+ (mysql.connector connection pool)
- **Auth:** JWT (python-jose) + bcrypt (passlib)
- **File Storage:** Local filesystem `./uploads/` (S3 in production)
- **Port:** 8000

### Project Structure
```
coz_code_backend/
├── run.py                  # Entry point: uvicorn server
├── seed.py                 # Seed DB with test data
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI app, CORS, routes, static mounts
│   ├── config.py           # Settings (DB credentials, JWT secret)
│   ├── database.py         # MySQL connection pool, fetch_one/all/execute helpers
│   ├── auth.py             # JWT creation, password hashing, get_current_user dependency
│   ├── pin_resolver.py     # India Post API → PIN code lookup + cache in DB
│   └── routes/
│       ├── __init__.py
│       ├── auth.py         # /auth/* — register, login, pin-lookup, me
│       ├── submissions.py  # /submissions/* — submit, list, edit
│       ├── citizen.py      # /citizen/* — dashboard, notifications
│       ├── mp.py           # /mp/* — dashboard, clusters, decide, budget
│       └── scheduler.py    # /scheduler/run — trigger pipeline subprocess
└── uploads/                # Audio/image files stored here
    └── {submission_uuid}/
```

### API Endpoints

**Auth (`/auth`)**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/auth/pin-lookup/{pin}` | No | Auto-fill location from PIN (India Post API + DB cache) |
| POST | `/auth/register` | No | Register citizen (phone + PIN + password → auto-fill location) |
| POST | `/auth/login` | No | Login → JWT token |
| GET | `/auth/me` | JWT | Current user profile |

**Submissions (`/submissions`)**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/submissions/` | JWT(user) | Submit issue (multipart: text/audio/image + PIN) |
| GET | `/submissions/my` | JWT(user) | List citizen's submissions |
| GET | `/submissions/{id}` | JWT(user) | Submission detail + media + status history |
| PUT | `/submissions/{id}` | JWT(user) | Edit (same-day only, before 23:30) |

**Citizen Dashboard (`/citizen`)**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/citizen/dashboard` | JWT(user) | KPIs + area stats + category breakdown |
| GET | `/citizen/notifications` | JWT(user) | Latest 50 notifications |
| PUT | `/citizen/notifications/{id}/read` | JWT(user) | Mark notification read |

**MP Dashboard (`/mp`)**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/mp/dashboard` | JWT(mp) | Full dashboard: KPIs, budget, trends |
| GET | `/mp/clusters` | JWT(mp) | Ranked clusters (filter by status/category) |
| GET | `/mp/clusters/{id}` | JWT(mp) | Cluster detail + submissions + media + scores |
| POST | `/mp/clusters/{id}/decide` | JWT(mp) | Approve/reject with reason + amount |
| GET | `/mp/decisions` | JWT(mp) | Recent decisions list |
| GET | `/mp/budget` | JWT(mp) | Budget overview + history |

**Scheduler (`/scheduler`)**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/scheduler/run` | No | Manually trigger Layer 2→5 pipeline |

### Database Config
```
Host: localhost:3306
User: root
Database: peoples_priorities
JWT_SECRET: pp-hackathon-secret-change-in-production
JWT_EXPIRE: 24 hours
```

### Test Credentials
- **Citizen:** `9876543210` / `test1234` (also 9876543211-9876543215)
- **MP (Jagatsinghpur):** `9000000001` / `mp123456`

### Key Implementation Notes
- **PIN resolver** uses India Post API (`api.postalpincode.in`) for real-time lookup, caches results in `pin_code_directory` table
- **District ≠ Lok Sabha Constituency** — hardcoded mapping dict handles this (e.g., PIN 752110 is Puri district but Jagatsinghpur constituency)
- **File uploads** saved to `./uploads/{submission_uuid}/` with path stored in `submission_media.file_url`
- **Tracking IDs** format: `PP-2026-00001` (auto-generated)
- **Edit window:** Citizens can edit submissions until 23:30 same day only
- **Multipart form** for submissions: `submission_pin_code`, `input_type`, `raw_text?`, `raw_language?`, `audio_file?`, `image_file?`

---

## DATABASE SCHEMA (MySQL 8.0.13+ — 19 Tables)

**Schema diagram:** https://dbdiagram.io/d/69305fd5d6676488ba74c3e8

### Tables by Layer

**Layer 1 — Data Intake:**
- `pin_code_directory` — Static: PIN → location + constituency
- `users` — Citizens (role=user) + MPs (role=mp). Phone+password auth.
- `raw_submissions` — Sacred raw citizen input (NEVER modified after creation)
- `submission_media` — Audio/image file URLs + metadata

**Layer 2 — Processing:**
- `processed_submissions` — AI-processed English text + spam flags (1:1 with raw)
- `processing_queue` — Pipeline job tracker (ASR/OCR/translate stages)

**Layer 3 — Clustering:**
- `demand_clusters` — Grouped similar issues (what MP sees on dashboard)
- `cluster_submissions` — Mapping: which submissions → which cluster
- `mplads_categories` — 14 MPLADS sector definitions

**Layer 4 — Enrichment:**
- `data_sources` — Pre-loaded Census/UDISE+/IPHS/JJM/PMGSY data
- `infrastructure_norms` — Government standards for gap calculation
- `category_severity` — Severity scores per MPLADS category

**Layer 5 — Scoring:**
- `scoring_weights` — Configurable 7-factor weights per constituency
- `cluster_scores` — Full score breakdown per cluster (raw → normalized → weighted → final)

**Layer 6 — MP Dashboard:**
- `mp_decisions` — MP approve/reject with mandatory reason
- `budget_tracker` — Live budget per constituency per FY (₹5Cr default)
- `mplads_fund_history` — Historical spending from eSAKSHI
- `notifications` — All user notifications
- `submission_status_log` — Append-only audit trail

### Key Schema Rules
- `raw_submissions` is SACRED — never modified after creation
- `submission_status_log` is APPEND-ONLY — never updated or deleted
- Two PIN codes: `home_pin_code` (registration) + `submission_pin_code` (problem location)
- `demand_clusters.rank` uses backticks (`` `rank` ``) — reserved word in MySQL 8+
- All UUIDs: `CHAR(36) DEFAULT (UUID())` — requires MySQL 8.0.13+
- JSON columns use `DEFAULT (JSON_ARRAY())` or `DEFAULT (JSON_OBJECT())`

---

## SCORING ENGINE (Layer 5)

### 7-Factor Weighted Formula
| # | Factor | Symbol | Weight | Description |
|---|--------|--------|--------|-------------|
| 1 | Demand Volume | D | 0.18 | `ln(1+users)/ln(1+N_max)` — log-scaled to prevent gaming |
| 2 | Category Severity | S | 0.20 | Static lookup (Water=1.0, Health=0.95, Education=0.85, Roads=0.75) |
| 3 | Vulnerability | V | 0.15 | Composite: 0.35×SC/ST% + 0.30×BPL% + 0.20×(1-literacy) + 0.15×(1-female_literacy) |
| 4 | Infrastructure Gap | I | 0.20 | Reality vs govt standard — **THE ANTI-GAMING ANCHOR** |
| 5 | Feasibility | F | 0.10 | Budget available + cost efficiency + MPLADS eligibility |
| 6 | Recency & Trend | R | 0.07 | How old + accelerating/declining |
| 7 | Historical Bias | H | 0.10 | `1 - (sector_spend%/max_spend%)` — boosts underfunded sectors |

```
BASE_SCORE = 0.18×D + 0.20×S + 0.15×V + 0.20×I + 0.10×F + 0.07×R + 0.10×H
FINAL_SCORE = BASE_SCORE × spam_decay × concentration_penalty
PRIORITY_SCORE = FINAL_SCORE × 10  (displayed as X.X out of 10)
```

### Anti-Gaming Modifiers
- **spam_decay:** If `unique_users/total_submissions < 0.3` → ×0.70 penalty
- **concentration_penalty:** If >25% demand from single PIN → ×0.80 penalty
- **Log-scaled demand:** `ln(501)/ln(501) = 1.0` vs `ln(51)/ln(501) = 0.63` — 500 organized submissions don't crush 50 genuine ones

### Infrastructure Gap (Factor I)
Compares real government data against official norms:
- EDUCATION: Schools per pop (RTE: 1/300), teacher ratio (RTE: 30:1), toilet coverage
- HEALTH: PHC per pop (IPHS 2022: 1/30K plain, 1/20K tribal), doctors (WHO: 1/1K)
- WATER: Tap coverage (JJM: 100%), ROADS: Habitation connectivity (PMGSY: 100%)

Even if 1000 fake submissions demand a road, if PMGSY data shows road exists (gap=0.05), cluster can't rank high.

---

## LAYER 4 DATA SOURCES

Pre-loaded from government portals into `data_sources` table:

| Source | Portal | Data |
|--------|--------|------|
| Census 2011 | censusindia.gov.in | Population, SC/ST%, literacy, gender ratio |
| SECC 2011 | secc.gov.in | BPL%, deprivation indicators |
| UDISE+ | udiseplus.gov.in | Schools, enrollment, teachers, infrastructure |
| HMIS/IPHS | hmis.nhp.gov.in | PHC/CHC, doctors, beds |
| JJM | ejalshakti.gov.in | Tap water coverage % |
| PMGSY | pmgsygeosadak.dord.gov.in | Road connectivity, habitations |
| Saubhagya | saubhagya.gov.in | Household electrification % |
| Swachh Bharat | sbm.gov.in | Toilet coverage, ODF status |
| eSAKSHI | mplads.gov.in | Past MPLADS spending by sector |

**One-stop:** NDAP (ndap.niti.gov.in) has most datasets pre-processed.

---

## DATA FLOW

```
CITIZEN REGISTERS → users (phone+PIN+password → auto-fill location)
    │
    ▼ CITIZEN SUBMITS ISSUE
raw_submissions (raw_text/input_type/PIN → auto-fill location)
    ├──► submission_media (audio/image files → local uploads/)
    │
    ▼ LAYER 2: AI PIPELINE (nightly 23:30)
processing_queue (stage: asr→ocr→translate→spam_check)
    ▼
processed_submissions (translated English text + spam flag)
    │
    ▼ LAYER 3: CLUSTERING
demand_clusters (group similar processed submissions)
    ├──► cluster_submissions (maps: submissions → clusters)
    ├── Check mplads_categories → is_mplads_eligible?
    │     ├── YES → proceed
    │     └── NO → reject + notify users
    │
    ▼ LAYERS 4 & 5: ENRICH + SCORE
data_sources + infrastructure_norms → priority_score + rank
    │
    ▼ LAYER 6: MP DASHBOARD
mp_decisions (approve/reject with reason + allocated amount)
    ├──► budget_tracker (deduct from ₹5Cr)
    ├──► notifications → all users in cluster
    └──► submission_status_log (audit trail)
```

---

## KEY DESIGN DECISIONS

1. **MySQL 8.0.13+** (not PostgreSQL) — team decision
2. **Two PIN codes:** Home (registration) + Problem location (submission)
3. **Two roles only:** `user` (citizen) and `mp`
4. **District ≠ Lok Sabha Constituency** — must use proper mapping
5. **Nightly scheduler at 23:30** — processes new submissions through Layers 2-5
6. **Edit window:** Users can edit submissions until 23:30 same day
7. **Never delete originals** — raw data is sacred, processing creates new records
8. **Log-scaled demand** — prevents organized brigading
9. **Infrastructure gap as anti-gaming anchor** — real data overrides fake demand
10. **Keyword-based MPLADS categorization** — no LLM needed for hackathon
11. **13 Indian languages** in UI (i18n), all processing normalizes to English
12. **File storage:** Local `uploads/` for hackathon, S3 for production
