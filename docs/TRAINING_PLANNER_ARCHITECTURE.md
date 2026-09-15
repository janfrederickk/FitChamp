# Training Planner — Product & Architecture Plan

> **Status:** Planning document for future development  
> **Last updated:** 2026-09-15  
> **Stack:** .NET 10, ASP.NET Core MVC, Razor, EF Core, PostgreSQL, Identity, HTMX, Hangfire, Serilog, OpenTelemetry

---

## Table of contents

1. [Product summary](#1-product-summary)
2. [Main user journeys](#2-main-user-journeys)
3. [Functional requirements](#3-functional-requirements)
4. [Non-functional requirements](#4-non-functional-requirements)
5. [MVP scope](#5-mvp-scope)
6. [Features excluded from MVP](#6-features-excluded-from-mvp)
7. [Domain model](#7-domain-model)
8. [Aggregate boundaries](#8-aggregate-boundaries)
9. [Entity relationships](#9-entity-relationships)
10. [PostgreSQL schema proposal](#10-postgresql-schema-proposal)
11. [Activity import architecture](#11-activity-import-architecture)
12. [Intervals.icu integration](#12-intervalsicu-integration)
13. [Future Zwift integration](#13-future-zwift-integration)
14. [Future Garmin integration](#14-future-garmin-integration)
15. [GitHub Action integration](#15-github-action-integration)
16. [Recurring training design](#16-recurring-training-design)
17. [Availability design](#17-availability-design)
18. [Goal and competition design](#18-goal-and-competition-design)
19. [Planned workout model](#19-planned-workout-model)
20. [Workout step model](#20-workout-step-model)
21. [Planned vs actual matching](#21-planned-vs-actual-matching)
22. [RPE / Feeling handling](#22-rpe--feeling-handling)
23. [Training load model](#23-training-load-model)
24. [TrainingContext](#24-trainingcontext)
25. [OpenAI integration](#25-openai-integration)
26. [AI structured output proposal](#26-ai-structured-output-proposal)
27. [Training plan validation](#27-training-plan-validation)
28. [Background jobs](#28-background-jobs)
29. [Synchronization and idempotency](#29-synchronization-and-idempotency)
30. [MVC page structure](#30-mvc-page-structure)
31. [Project and folder structure](#31-project-and-folder-structure)
32. [Security](#32-security)
33. [Logging / observability](#33-logging--observability)
34. [Testing strategy](#34-testing-strategy)
35. [Docker development environment](#35-docker-development-environment)
36. [Ordered implementation roadmap](#36-ordered-implementation-roadmap)
37. [Architectural risks](#37-architectural-risks)
38. [Decisions still required before coding](#38-decisions-still-required-before-coding)
39. [Recommended first vertical slice](#39-recommended-first-vertical-slice)

---

## 1. Product summary

**Training Planner** is a personal endurance-training platform that combines a local-first training model, adaptive AI-assisted planning, and integrations with external fitness services (initially Intervals.icu). The athlete defines goals, availability, fixed recurring sessions, and preferences; the system imports completed activities, compares planned vs actual performance, and proposes training plans that the user reviews and approves before they are stored and optionally exported.

### Core principles

| Principle | Meaning |
|-----------|---------|
| **Local-first** | PostgreSQL is the source of truth for planning, calendar, and AI context |
| **Provider-agnostic domain** | Intervals.icu, Zwift, Garmin, GitHub Action are Infrastructure adapters |
| **Proposal → approval** | AI and chat never silently mutate the calendar |
| **Best-available stress** | Objective, subjective, and assumed load are composed, not fabricated |
| **Single user now, multi-user later** | Every entity is scoped by `AthleteId`; Identity is in place from day one |

### Basic workflow

```
Completed activities
+ Goals
+ Fixed training
+ Availability
+ Training history
+ RPE / Feeling
        ↓
Training Planner
        ↓
AI-generated training proposal (GPT 5.6)
        ↓
Validation (TrainingPlanValidator)
        ↓
User approval
        ↓
Training calendar
        ↓
Intervals.icu (export)
```

### Tech stack

- .NET 10, ASP.NET Core MVC, Razor Views
- Entity Framework Core, PostgreSQL
- ASP.NET Core Identity
- HTMX (where useful), Bootstrap 5 (MVP)
- HttpClientFactory, Hangfire, Serilog, OpenTelemetry
- xUnit, Testcontainers, Docker

### Solution structure

```
TrainingPlanner.sln
src/
  TrainingPlanner.Domain
  TrainingPlanner.Application
  TrainingPlanner.Infrastructure
  TrainingPlanner.Web
tests/
  TrainingPlanner.Domain.Tests
  TrainingPlanner.Application.Tests
  TrainingPlanner.Integration.Tests
```

Pragmatic Clean Architecture — avoid unnecessary enterprise complexity.

---

## 2. Main user journeys

### Journey A — Onboard and connect Intervals.icu

1. Register / log in.
2. Complete athlete profile (sports, zones, preferences).
3. Connect Intervals.icu (API key for MVP).
4. Trigger initial import (90–180 days).
5. View imported activities and sync status on dashboard.

### Journey B — Define constraints

1. Add A/B/C goals and competition dates.
2. Configure weekly availability and exceptions.
3. Add fixed recurring wrestling (locked, AI may not move).
4. Set sport-specific defaults (wrestling: default load, no RPE required).

### Journey C — AI plan next week

1. Open Planner → "Generate next 7 days".
2. System builds `TrainingContext`, calls OpenAI (GPT 5.6), receives structured proposal.
3. `TrainingPlanValidator` runs deterministic checks.
4. User reviews calendar diff + explanations.
5. User approves → planned workouts saved → export job pushes to Intervals.icu.

### Journey D — Train and adapt

1. Complete workout (recorded on device → Intervals.icu).
2. Background sync imports activity, matches to planned workout.
3. Planned vs actual stored (duration, load, RPE delta).
4. Next AI request includes this signal; planner may soften next session.

### Journey E — Weekly review

1. End of week: summaries computed.
2. User opens weekly review (volume, sport split, missed sessions, RPE/Feeling trends).
3. Optional AI narrative + next-week proposal → approval flow.

### Journey F — Wrestling via GitHub Action (post-MVP slice)

1. GitHub Action POSTs wrestling session to authenticated API.
2. Activity normalized and stored with assumed load.
3. Appears on calendar; included in training stress without fake RPE.

---

## 3. Functional requirements

### Identity & profile

- **FR-01:** User registration, login, password reset (Identity).
- **FR-02:** One athlete profile per user (MVP); model allows multiple later.
- **FR-03:** Sport profiles with zones (HR, power, pace), FTP, thresholds, preferences.

### Activities

- **FR-10:** Import activities from Intervals.icu (background, incremental).
- **FR-11:** Store normalized `TrainingActivity` in PostgreSQL.
- **FR-12:** Optional RPE, Feeling, notes; never require missing fields.
- **FR-13:** Provider link table for external IDs and deduplication.
- **FR-14:** Manual "Sync now" and scheduled sync.

### Calendar

- **FR-20:** Day / week / month views.
- **FR-21:** Display planned workouts, completed activities, races, rest, unavailable.
- **FR-22:** Drag-and-drop reschedule (respecting locked items).
- **FR-23:** Quick edit; workout status lifecycle.

### Planning

- **FR-30:** Recurring training rules + exceptions.
- **FR-31:** Availability rules + exceptions.
- **FR-32:** Goals and competitions with A/B/C priority.
- **FR-33:** Training phases (manual or derived).
- **FR-34:** Structured planned workouts with steps.
- **FR-35:** Workout template library (MVP: basic CRUD + schedule).

### AI

- **FR-40:** Generate proposals from `TrainingContext` (structured JSON via GPT 5.6).
- **FR-41:** All calendar changes require approval.
- **FR-42:** Explanations stored with proposals.
- **FR-43:** Coach chat with proposal-only mutations (post-MVP).

### Validation

- **FR-50:** Deterministic `TrainingPlanValidator` before approval.
- **FR-51:** Human-readable errors and warnings.

### Integrations

- **FR-60:** Export planned workouts to Intervals.icu (idempotent upsert).
- **FR-61:** Sync logs and status UI.
- **FR-62:** GitHub Action endpoint (authenticated, idempotent) — designed in MVP, implement in slice 2.

### Analytics

- **FR-70:** Planned vs actual comparison.
- **FR-71:** Training load / volume summaries.
- **FR-72:** Weekly review aggregates.

---

## 4. Non-functional requirements

| Area | Requirement |
|------|-------------|
| **Availability** | App usable when Intervals.icu is down (cached data) |
| **Sync** | Incremental, idempotent, retryable, observable |
| **Performance** | Calendar pages read only PostgreSQL; no live provider calls |
| **Security** | Encrypted secrets; no tokens in logs |
| **Maintainability** | Pragmatic Clean Architecture; 4 projects |
| **Testability** | Domain + application unit tests; integration tests with Testcontainers |
| **Observability** | Structured logs, correlation IDs, OpenTelemetry traces/metrics |
| **Deployability** | Docker Compose for dev; containerized web + DB |

---

## 5. MVP scope

**In MVP:**

- User login (Identity)
- Athlete profile (core fields + zones)
- PostgreSQL + EF Core migrations
- Intervals.icu connection + activity import (90/180 day initial)
- Activity list/history
- Calendar (week primary; day/month basic)
- Recurring wrestling training (locked)
- Availability (weekly rules)
- Goals (basic types)
- Structured planned workouts + steps
- AI generate next 7 days (structured output, GPT 5.6)
- `TrainingPlanValidator`
- User approval workflow
- Store planned workouts
- Export workouts to Intervals.icu
- Import completed activities
- Planned vs actual matching (basic)
- Feed match results into next AI request
- Dashboard with next workout + sync status
- Hangfire jobs for import/export
- Serilog + basic OpenTelemetry

**MVP navigation:** Dashboard, Calendar, Activities, Goals, Planner, Integrations, Settings.

---

## 6. Features excluded from MVP

- Direct Garmin / Zwift API
- GitHub Action endpoint (designed, not built in MVP unless fast follow)
- Full workout library / AI template generation
- Coach chat
- Weekly review AI narrative
- Wellness import from Intervals.icu
- Multi-week (4-week) generation
- Advanced analytics
- Weather, nutrition, equipment
- Multi-user / coach mode
- Mobile native app
- Race prediction / medical readiness

---

## 7. Domain model

### Core enums (Domain)

```
Sport: Cycling, Running, Swimming, Wrestling, Strength, Other
ActivityType: Workout, Race, Commute, Recovery, Other
WorkoutStatus: Planned, Completed, PartiallyCompleted, Skipped, Cancelled
GoalType: Race, Distance, FinishTime, Ftp, Pace, BodyWeight, WeeklyVolume, GeneralFitness, BaseTraining
GoalPriority: A, B, C
TrainingPhaseType: Base, Build, Specialization, Peak, Taper, Recovery
Feeling: VeryPoor, Poor, Normal, Good, VeryGood
Intensity: Recovery, Easy, Moderate, Hard, VeryHard
ExternalProvider: IntervalsIcu, Zwift, Garmin, GitHubAction, Manual
EntityType: Activity, PlannedWorkout, Athlete
SyncDirection: Import, Export
ProposalStatus: Draft, PendingReview, Approved, Rejected, Superseded
```

### Key entities

| Entity | Role |
|--------|------|
| `Athlete` | Planning subject; links to Identity user |
| `AthleteProfile` | Preferences, limits, default days |
| `SportProfile` | Per-sport settings (wrestling defaults, zone refs) |
| `TrainingZoneSet` | HR / power / pace zones |
| `TrainingActivity` | Completed session (provider-independent) |
| `ActivityFeedback` | RPE, Feeling, notes (optional) |
| `PlannedWorkout` | Future/past planned session |
| `WorkoutStep` | Structured steps (owned by planned workout or template) |
| `WorkoutTemplate` | Reusable definition |
| `WorkoutCompletion` | Links planned ↔ actual + comparison metrics |
| `RecurringTrainingRule` | Weekly recurrence pattern |
| `RecurringTrainingException` | Skip/move/override |
| `AvailabilityRule` | Weekly capacity / sport constraints |
| `AvailabilityException` | Date-specific overrides |
| `Goal` | Target with priority and dates |
| `Competition` | Race on calendar |
| `TrainingPhase` | Date-bounded phase |
| `ExternalConnection` | Provider credentials metadata |
| `ExternalEntityLink` | Internal ↔ external ID mapping |
| `SyncState` | Per-connection cursor / watermark |
| `SyncLog` | Audit trail per sync run |
| `AIPlanningProposal` | Raw request + structured response + status |
| `TrainingSummary` | Precomputed rollups (daily/weekly) |

### TrainingActivity (provider-independent)

Fields to consider (all optional where not applicable):

- `Id`, `AthleteId`, `Sport`, `ActivityType`
- `StartTime`, `EndTime`, `Duration`, `Distance`, `ElevationGain`
- `AverageHeartRate`, `MaximumHeartRate`, `AveragePower`, `NormalizedPower`, `Cadence`, `Calories`
- `TrainingLoad`, `TrainingEffect`
- `ImportedAt`, `UpdatedAt`

RPE and Feeling live in `ActivityFeedback`, not on the activity itself.

Do not force fake data into missing fields (e.g. wrestling has no power; some activities have no RPE).

### Value objects

`Duration`, `Distance`, `Elevation`, `TrainingLoadScore`, `DateOnlyRange`, `TimeOnlyRange`, `WeekdaySchedule`

---

## 8. Aggregate boundaries

| Aggregate | Root | Consistency rule |
|-----------|------|------------------|
| **Athlete** | `Athlete` | Profile, sport profiles, zones updated together |
| **TrainingActivity** | `TrainingActivity` | Activity + optional feedback; links are separate |
| **PlannedWorkout** | `PlannedWorkout` | Steps and status change with workout |
| **WorkoutTemplate** | `WorkoutTemplate` | Template + steps |
| **RecurringTraining** | `RecurringTrainingRule` | Exceptions reference rule |
| **Availability** | `AvailabilityRule` set per athlete | Exceptions per rule or global |
| **Goal** | `Goal` | Independent lifecycle |
| **Competition** | `Competition` | Independent; referenced by planner |
| **ExternalConnection** | `ExternalConnection` | SyncState child |
| **AIPlanningProposal** | `AIPlanningProposal` | Immutable once approved; new proposal supersedes |

Cross-aggregate rules are enforced in Application services + validator, not inside aggregates.

---

## 9. Entity relationships

```
User (Identity) 1──1 Athlete
Athlete 1──* SportProfile
Athlete 1──* TrainingZoneSet
Athlete 1──* Goal
Athlete 1──* Competition
Athlete 1──* TrainingPhase
Athlete 1──* AvailabilityRule
Athlete 1──* RecurringTrainingRule
Athlete 1──* TrainingActivity
Athlete 1──* PlannedWorkout
Athlete 1──* WorkoutTemplate
Athlete 1──* ExternalConnection

TrainingActivity 1──0..1 ActivityFeedback
PlannedWorkout 1──* WorkoutStep
PlannedWorkout 0..1──1 WorkoutCompletion ──0..1── TrainingActivity
WorkoutTemplate 1──* WorkoutStep

RecurringTrainingRule 1──* RecurringTrainingException
AvailabilityRule 1──* AvailabilityException (optional)

ExternalEntityLink *──1 (Athlete scoped) polymorphic InternalEntityId + EntityType
SyncState 1──1 ExternalConnection
SyncLog *──1 ExternalConnection

AIPlanningProposal *──1 Athlete
AIPlanningProposal 1──* PlannedWorkout (after approval, optional FK)
```

---

## 10. PostgreSQL schema proposal

### Naming conventions

- Tables: snake_case plural (`training_activities`)
- PK: `uuid` (gen_random_uuid()) for domain entities; `bigint` for Identity tables
- All tenant data: `athlete_id uuid NOT NULL`

### Core tables

**athletes**

```sql
id, user_id (unique), display_name, created_at, updated_at
```

**athlete_profiles**

```sql
id, athlete_id (unique), max_hr, threshold_hr, ftp, preferred_target_type,
preferred_long_ride_day, preferred_rest_day, max_hard_sessions_per_week,
prefer_indoor, planning_notes, timezone, ...
```

**sport_profiles**

```sql
id, athlete_id, sport, default_intensity, default_planning_load,
rpe_required, feeling_required, is_enabled, ...
UNIQUE (athlete_id, sport)
```

**training_zone_sets** / **training_zones**

```sql
zone_set: id, athlete_id, sport, zone_type (hr|power|pace)
zone: id, zone_set_id, index, name, min_value, max_value
```

**training_activities**

```sql
id, athlete_id, sport, activity_type, name,
start_time timestamptz, end_time timestamptz,
duration_seconds, distance_meters, elevation_gain_meters,
avg_hr, max_hr, avg_power, normalized_power, avg_cadence, calories,
training_load, training_effect,
source_provider,  -- denormalized primary source for UI
imported_at, updated_at
```

**activity_feedback**

```sql
id, training_activity_id (unique), rpe smallint, feeling smallint, notes
```

**external_entity_links**

```sql
id, athlete_id, provider, entity_type, internal_entity_id,
external_id, external_updated_at, last_synced_at, content_hash,
UNIQUE (athlete_id, provider, entity_type, external_id)
```

**planned_workouts**

```sql
id, athlete_id, sport, name, scheduled_date, start_time, duration_seconds,
intensity, expected_rpe, planning_load, status, is_locked, is_optional,
source (manual|ai|recurring), recurring_rule_id nullable,
training_phase_id nullable, description, notes, created_at, updated_at
```

**workout_steps**

```sql
id, planned_workout_id nullable, workout_template_id nullable,
parent_step_id nullable,  -- for Repeat
sort_order, step_type, duration_seconds,
target_type, target_value, target_zone, notes
CHECK (planned_workout_id IS NOT NULL OR workout_template_id IS NOT NULL)
```

**workout_completions**

```sql
id, planned_workout_id (unique), training_activity_id nullable,
completion_status, planned_duration_seconds, actual_duration_seconds,
planned_load, actual_load, planned_intensity, actual_intensity,
expected_rpe, actual_rpe, completion_percentage, notes
```

**recurring_training_rules**

```sql
id, athlete_id, name, sport, by_day (int[]), start_time, duration_seconds,
valid_from, valid_until, is_locked, ai_may_move, default_intensity,
default_planning_load, rrule text nullable, timezone
```

**recurring_training_exceptions**

```sql
id, rule_id, exception_date, exception_type (cancelled|moved|override),
override_start_time, override_duration, notes
UNIQUE (rule_id, exception_date)
```

**availability_rules**

```sql
id, athlete_id, day_of_week, max_duration_seconds,
allowed_sports (int[]), notes
UNIQUE (athlete_id, day_of_week)
```

**availability_exceptions**

```sql
id, athlete_id, start_date, end_date, exception_type,
max_duration_seconds nullable, is_unavailable, notes
```

**goals**

```sql
id, athlete_id, name, description, sport, goal_type, priority,
target_date, target_value, current_value, active, archived, created_at
```

**competitions**

```sql
id, athlete_id, name, date, sport, priority, target, notes
```

**training_phases**

```sql
id, athlete_id, phase_type, start_date, end_date, notes
```

**external_connections**

```sql
id, athlete_id, provider, display_name, is_enabled,
encrypted_credentials, token_expires_at, scopes, created_at
UNIQUE (athlete_id, provider)
```

**sync_states**

```sql
id, external_connection_id (unique), last_successful_sync_at,
cursor_json, initial_import_completed_at, last_error, consecutive_failures
```

**sync_logs**

```sql
id, external_connection_id, direction, started_at, completed_at,
status, records_processed, records_created, records_updated,
error_message, correlation_id
```

**ai_planning_proposals**

```sql
id, athlete_id, request_type, user_instruction, training_context_snapshot jsonb,
structured_response jsonb, validation_result jsonb, explanation text,
status, model_used, prompt_tokens, completion_tokens,
created_at, reviewed_at
```

**training_summaries**

```sql
id, athlete_id, period_type (day|week), period_start,
total_duration_seconds, total_load, sport_breakdown jsonb,
avg_rpe, feeling_distribution jsonb, planned_vs_actual jsonb
UNIQUE (athlete_id, period_type, period_start)
```

### Indexes

- `training_activities (athlete_id, start_time DESC)`
- `training_activities (athlete_id, sport, start_time)`
- `planned_workouts (athlete_id, scheduled_date)`
- `competitions (athlete_id, date)`
- `external_entity_links (athlete_id, provider, entity_type, external_id)` UNIQUE
- `sync_logs (external_connection_id, started_at DESC)`

---

## 11. Activity import architecture

```
Intervals.icu
      ↓
Hangfire ImportActivitiesJob
      ↓
IActivityProvider (Infrastructure)
      ↓
ExternalActivity DTO (Infrastructure)
      ↓
ActivityNormalizer (Application)
      ↓
TrainingActivity (Domain)
      ↓
PostgreSQL
      ↓
calendar / analytics / AI planner
```

The rest of the system must not care where an activity originally came from.

### Provider interface

```csharp
public interface IActivityProvider
{
    ExternalProvider Provider { get; }
    Task<ActivityImportBatch> FetchActivitiesAsync(
        ActivityImportCursor cursor,
        CancellationToken cancellationToken);
}

public sealed record ActivityImportBatch(
    IReadOnlyList<ExternalActivity> Activities,
    ActivityImportCursor NextCursor,
    bool HasMore);
```

**Why batch + cursor:** Supports pagination, rate limits, and resumable imports better than a single date-range call.

`ExternalActivity` stays in **Infrastructure**; `ActivityNormalizer` maps to domain `TrainingActivity` + `ExternalEntityLink`.

### Implementations

| Provider | MVP | Layer |
|----------|-----|-------|
| `IntervalsIcuActivityProvider` | Yes | Infrastructure |
| `ZwiftActivityProvider` | Future | Infrastructure |
| `GarminActivityProvider` | Future | Infrastructure |
| GitHub Action | Via API endpoint | Web + Application |

### Duplicate prevention

1. **Primary:** unique `(athlete_id, provider, entity_type, external_id)`.
2. **Secondary (future cross-provider):** fingerprint `(athlete_id, sport, start_time ± 2min, duration ± 5%)` → suggest merge; do not auto-merge in MVP.

### External ID example

```
Internal activity: 42
Intervals.icu:       12345
Zwift (future):      98765
Garmin (future):     abc123
```

All stored in `external_entity_links` for the same `internal_entity_id` when the same ride appears through multiple providers.

---

## 12. Intervals.icu integration

Intervals.icu is the main activity source for MVP and also the export target for planned workouts.

### Import

- **Infrastructure:** `IntervalsIcuApiClient` (HttpClientFactory typed client), `IntervalsIcuActivityProvider`, DTOs mirroring API.
- **Auth:** API key in header (Intervals.icu documented pattern) stored encrypted in `external_connections`.
- **Fields mapped:** sport, times, duration, distance, elevation, HR, power, NP, load, ICU RPE/Feeling (normalized), name, type.
- **Updates:** use `external_updated_at` from provider; upsert if newer than local `updated_at`.
- **Do not** query Intervals.icu live for every page request.

### Export (workouts)

```csharp
public interface IWorkoutPublisher
{
    ExternalProvider Provider { get; }
    Task<WorkoutPublishResult> PublishAsync(
        PlannedWorkout workout,
        ExternalEntityLink? existingLink,
        CancellationToken cancellationToken);
    Task DeleteOrCancelAsync(ExternalEntityLink link, CancellationToken ct);
}
```

- **Idempotency:** if link exists → update; else create; store returned external ID in `external_entity_links`.
- **Conflict:** if external modified since last sync → flag in UI; do not overwrite blindly.
- **Do not** blindly create duplicate planned workouts in Intervals.icu.

### Alternatives considered

- **Single generic `IExternalIntegration`:** rejected — import and export have different concerns.
- **Live Intervals.icu on calendar load:** rejected — violates local-first principle.

---

## 13. Future Zwift integration

Do **not** implement in MVP. Architect for it:

```
Zwift
  ↓
ZwiftActivityProvider (Infrastructure)
  ↓
same normalization pipeline
  ↓
TrainingActivity
  ↓
PostgreSQL
```

- Zwift-specific OAuth and activity DTOs stay isolated in Infrastructure.
- Calendar, analytics, AI planner, weekly review, and planned-vs-actual logic require **no changes**.
- Optional future: `ZwiftWorkoutPublisher` implementing `IWorkoutPublisher` for ZWO export.

---

## 14. Future Garmin integration

Do **not** require direct Garmin integration for MVP.

Later possibilities:

- Garmin activity import
- Garmin Training API / workout push
- RPE, Feeling, FIT files

All via Infrastructure adapters. Existing wrestling FIT generator in this repo can remain separate; activities may arrive via Intervals.icu sync (Garmin → Intervals.icu) or direct GitHub Action POST.

---

## 15. GitHub Action integration

### Recommended approach: API key per athlete + idempotent POST

**Endpoint:** `POST /api/external/activities`

**Auth:** `Authorization: Bearer <athlete_api_key>` (generated in Settings → API Keys; stored hashed).

**Request body:**

```json
{
  "provider": "GitHubAction",
  "externalId": "ringen-2026-09-15-workflow-42",
  "sport": "Wrestling",
  "name": "Ringen Training",
  "startTime": "2026-09-15T17:00:00Z",
  "durationSeconds": 5400,
  "averageHeartRate": 158
}
```

**Flow:**

1. Authenticate → resolve `athlete_id`.
2. Check `external_entity_links` for duplicate `externalId` → return 200 with existing ID (idempotent).
3. Normalize → `TrainingActivity` without RPE/Feeling.
4. Apply `SportProfile` defaults for wrestling load.
5. Optionally trigger `MatchActivitiesToPlannedWorkoutsJob`.

**Requirements:** authenticated, idempotent, external activity ID, wrestling support, no RPE/Feeling required.

**MVP:** Design documented; implement in vertical slice 2 (after Intervals.icu import works).

**Alternatives:**

- HMAC signature with shared secret: stronger but more complex for GitHub Actions.
- OAuth: overkill for single-user automation.

---

## 16. Recurring training design

### Model: rule + exceptions (not hundreds of rows)

**`RecurringTrainingRule`** stores:

- Weekly pattern: `DaysOfWeek` + `StartTime` + `Duration`
- Validity: `ValidFrom` / `ValidUntil`
- Flags: `IsLocked`, `AiMayMove`
- Defaults: intensity, planning load

**Example:**

```
Wrestling
Tuesday   19:00–20:30
Thursday  19:00–20:30
Fixed: yes
AI may move: no
Default intensity: hard
```

### Materialization strategy

- **Do not** pre-insert years of rows.
- **Calendar query service** expands rules into **virtual occurrences** for visible range (e.g. ±3 months).
- **Persist `PlannedWorkout`** only when:
  - user edits a single occurrence,
  - AI proposal approved,
  - export to Intervals.icu needs stable ID.

### Exceptions

| Type | Behavior |
|------|----------|
| Cancelled | Hide occurrence |
| Holiday/Vacation | Cancel or skip via exception date range |
| Moved | `override_start_time` + date |
| Special | Override duration/intensity |

**Link:** generated/approved instances reference `recurring_rule_id` for traceability.

**Alternative:** full RRULE (iCal). **Recommendation:** start with weekly bitmask + exceptions; add RRULE text field later if needed.

---

## 17. Availability design

**Weekly `AvailabilityRule`** per `DayOfWeek`:

- `MaxDuration`
- `AllowedSports` (empty = all)

**Example:**

| Day | Constraint |
|-----|------------|
| Monday | max 90 min |
| Tuesday | wrestling only |
| Wednesday | max 120 min |
| Thursday | wrestling only |
| Friday | max 60 min |
| Saturday | max 5h |
| Sunday | max 3h |

**`AvailabilityException`** for date ranges:

- `IsUnavailable` (hard block)
- `MaxDuration` override
- `Notes` (work trip, vacation, family event)

**AI usage:** `TrainingContext` includes resolved availability for planning horizon (next 14–28 days).

**Validator:** no planned workout may exceed day max duration or disallowed sport.

Availability is separate from recurring training.

---

## 18. Goal and competition design

### Goals

Support multiple goals with types: Race, Distance, FinishTime, FTP, Pace, BodyWeight, WeeklyVolume, GeneralFitness, BaseTraining.

Properties: Name, Description, Sport, GoalType, Priority, TargetDate, TargetValue, CurrentValue, Active, Archived.

**Example:** Rad am Ring 2027, Priority A, Target lap time: 55 minutes.

### Competitions

Fields: Name, Date, Sport, Priority (A/B/C), Target, Notes.

Competitions appear in the training calendar.

### Planner rules

- **A-race:** never auto-moved by AI.
- **B/C:** fixed date but intensity placement flexible.
- Goals inform `TrainingPhase` suggestions and AI context.

**Separation:** `Competition` is a dated event; `Goal` may exist without a single date (e.g. GeneralFitness).

---

## 19. Planned workout model

Planned workouts and completed activities are **separate entities**.

```
PlannedWorkout
├── identity & scheduling (date, time, duration)
├── sport, intensity, expected RPE, planning load
├── status: Planned | Completed | PartiallyCompleted | Skipped | Cancelled
├── flags: IsLocked, IsOptional
├── provenance: Manual | AiProposal | RecurringRule
├── structured steps (optional for simple sessions)
└── external sync state via ExternalEntityLink
```

**Example:**

- Planned: Sunday, 120 min, Z2, Expected RPE 3
- Actual (linked via WorkoutCompletion): 108 min, Average HR 138, RPE 5, Feeling Normal

Simple session: "90 min Z2" with no steps. Structured session: child `WorkoutStep` rows.

---

## 20. Workout step model

### Step types

Warmup, Steady, Interval, Recovery, Repeat, Cooldown, Open

### Targets

HeartRateZone, HeartRateBpm, PowerZone, Watts, PercentFtp, Pace, Cadence, Rpe, FreeRide

### Example

```
90 min endurance + tempo
  15 min Z1
  50 min Z2
  3x:
    5 min Z3
    5 min Z2
  10 min Z1
```

### Repeat step

`parent_step_id` groups children; `RepeatCount` on parent.

**Export adapters** (Infrastructure) translate internal steps → Intervals.icu workout format / future ZWO / Garmin.

**Domain** never references provider step syntax.

### Workout library (post-MVP / partial MVP)

Reusable templates: Recovery 45, Z2 60, Sweet Spot 3x12, Threshold 4x8, VO2max 5x4, Long Endurance.

Users can create, edit, save, duplicate, schedule, generate using AI, send to Intervals.icu.

---

## 21. Planned vs actual matching

### WorkoutCompletion

Created by `MatchActivitiesToPlannedWorkoutsJob` (Hangfire) after import.

### Matching heuristics (priority order)

1. Manual user link (always wins).
2. Same day + same sport + planned time ± 3h + duration overlap > 50%.
3. External link if workout was exported and activity references workout ID (Intervals.icu event id).

### Computed fields

- `completion_percentage` = actual_duration / planned_duration
- `rpe_delta` = actual_rpe - expected_rpe
- `load_delta`, intensity comparison

### Statuses

- Full match → `Completed`
- Partial duration → `PartiallyCompleted`
- No activity → remains `Planned` until skipped or week closes

### Adaptive planning example

```
Planned:  90 min Z2, Expected RPE 3
Actual:   105 min, RPE 7, Feeling Poor
→ Planner recognizes session was significantly harder than expected
→ Next recommendation should consider this
```

**Planner feedback:** summaries in `TrainingContext.RecentPlannedVsActual`.

---

## 22. RPE / Feeling handling

- Stored in `ActivityFeedback` (optional, 0..1 per activity).
- **Feeling** normalized to domain enum; provider-specific scales mapped in Infrastructure.
- **Missing values:** normal; validator and AI must not require them.
- **Wrestling:** `SportProfile.RpeRequired = false`, `FeelingRequired = false`; use `default_planning_load` instead.
- **Never fabricate** RPE for AI or analytics.

### Internal Feeling model

VeryPoor, Poor, Normal, Good, VeryGood

---

## 23. Training load model

### Training stress sources

| Source | Examples |
|--------|----------|
| **Objective** | duration, HR, power, provider training load |
| **Subjective** | RPE, Feeling |
| **Assumed** | recurring wrestling default load, manually configured load |

The planner uses the best available information.

### ITrainingStressCalculator (Application)

Priority per activity:

1. Provider `training_load` if present.
2. Estimated from duration × intensity zone × sport factor.
3. RPE-based TRIMP-style estimate if no power/HR load.
4. Sport default (wrestling) or recurring rule default.

```csharp
public sealed record TrainingStress(
    decimal Load,
    TrainingStressSource Source,
    string? Explanation);
```

**Weekly rollups** stored in `training_summaries` for fast `TrainingContext` building.

### Wrestling defaults

```
Wrestling
90 min
Default intensity: Hard
Default planning load: 75
RPE required: false
Feeling required: false
```

AI planner treats wrestling as real training stress without fabricating RPE.

---

## 24. TrainingContext

Built by `ITrainingContextBuilder` (Application) from **PostgreSQL only**. The AI planner must not directly query external APIs.

```csharp
public sealed class TrainingContext
{
    public AthleteProfileSnapshot Athlete { get; init; }
    public IReadOnlyList<GoalSnapshot> Goals { get; init; }
    public IReadOnlyList<CompetitionSnapshot> Competitions { get; init; }
    public TrainingPhaseSnapshot? CurrentPhase { get; init; }
    public TrainingLoadSummary LoadSummary { get; init; }      // 4–6 weeks
    public RpeTrend RpeTrend { get; init; }
    public FeelingTrend FeelingTrend { get; init; }
    public IReadOnlyList<ActivitySummary> RecentActivities { get; init; } // last 10–14, summarized
    public IReadOnlyList<PlannedVsActualSummary> RecentVariance { get; init; }
    public CalendarSnapshot CurrentWeek { get; init; }
    public IReadOnlyList<FixedTrainingOccurrence> UpcomingFixedTraining { get; init; }
    public IReadOnlyList<AvailabilityDay> ResolvedAvailability { get; init; }
    public IReadOnlyList<PlannedWorkoutSnapshot> ExistingPlan { get; init; }
    public PlanningPreferences Preferences { get; init; }
}
```

**Token budget:** send summaries, not raw streams. Full activity detail only when regenerating a single day.

### Included data

AthleteProfile, Goals, Competitions, TrainingPhase, Recent activities, Training history summary, Training load summary, RPE trend, Feeling trend, Current week, Upcoming fixed training, Availability, Planned workouts, Recent planned vs actual data, Training preferences.

---

## 25. OpenAI integration

- **Infrastructure:** `OpenAiTrainingPlannerClient` implements `IAiTrainingPlanner`.
- **HttpClientFactory** typed client; API key from configuration/secret store.
- **Application** orchestrates: build context → call AI → deserialize → validate → persist proposal.
- **AI never calls** Intervals.icu or writes workouts directly.

### Model configuration

```json
"OpenAi": {
  "DefaultModel": "gpt-5.6",
  "FastModel": "gpt-5.6",
  "FallbackModel": "gpt-4o-mini",
  "MaxTokens": 4096,
  "Temperature": 0.4
}
```

### Model routing

| Request type | Model |
|--------------|-------|
| Generate next 7 days | gpt-5.6 |
| Generate next 4 weeks | gpt-5.6 |
| Regenerate one workout | gpt-5.6 |
| Make easier / harder / shorten | gpt-5.6 (fast variant if available) |
| Coach chat | gpt-5.6 |
| Weekly review narrative | gpt-5.6 |
| "What should I train today?" | gpt-5.6 |

**GPT 5.6 is the default planning model.** GPT 4o-mini is a configurable fallback for resilience and dev cost control.

### Interface

```csharp
public interface IAiTrainingPlanner
{
    Task<AIPlanningProposalResult> GenerateProposalAsync(
        TrainingContext context,
        PlanningRequest request,
        CancellationToken cancellationToken);
}

public enum AiModelPreference
{
    Default,   // → gpt-5.6
    Fast,      // → gpt-5.6 fast variant if available
    Quality    // → gpt-5.6 with higher reasoning effort if supported
}
```

### Implementation notes

- Model ID is **configuration**, not hardcoded.
- Log `model`, `prompt_tokens`, `completion_tokens`, `duration_ms` (no prompt content in prod).
- **Fallback chain:** gpt-5.6 → gpt-4o-mini on rate limit or model-unavailable (Polly in Infrastructure).
- **Retry:** transient HTTP errors with Polly.

### AI features (MVP and beyond)

- Generate next workout / next week / next 4 weeks
- Regenerate one workout
- Make easier / harder / shorten
- Convert indoor/outdoor, HR/power target
- Replan after missed workout / rest of week
- Explain why workout changed
- "What should I train today?"
- Weekly review
- Coach chat (post-MVP)

All changes are proposals requiring user approval.

### Explainable AI

Store sufficient planning metadata so explanations can be reproduced.

**Example:**

> Wednesday threshold session was changed to recovery because:
> - previous ride had RPE 3 points above expected
> - Feeling was Poor
> - hard wrestling session was completed Tuesday
> - another fixed wrestling session is scheduled Thursday

---

## 26. AI structured output proposal

Use OpenAI **structured outputs** (JSON Schema) or tool calling with strict schema.

### Response schema

```json
{
  "explanation": "string",
  "confidence": 0.0,
  "workouts": [
    {
      "date": "2026-09-21",
      "sport": "Cycling",
      "name": "Endurance",
      "durationMinutes": 120,
      "intensity": "Easy",
      "expectedRpe": 3,
      "planningLoad": 65,
      "isLocked": false,
      "steps": [
        { "type": "Warmup", "durationMinutes": 15, "targetType": "HeartRateZone", "targetZone": 1 },
        { "type": "Steady", "durationMinutes": 90, "targetType": "HeartRateZone", "targetZone": 2 },
        { "type": "Cooldown", "durationMinutes": 15, "targetType": "HeartRateZone", "targetZone": 1 }
      ]
    }
  ],
  "warnings": ["string"]
}
```

### Persistence

Store full JSON in `ai_planning_proposals.structured_response` + `training_context_snapshot` for reproducible explanations.

Store `model_used`, `prompt_tokens`, `completion_tokens` for cost tracking.

**Do not** rely on unstructured free text for important workout data.

**Alternative:** free-text parsing — rejected for reliability.

---

## 27. Training plan validation

`ITrainingPlanValidator` — pure Application service, rules as small classes.

Do not rely only on AI.

| Rule | Severity |
|------|----------|
| No overlapping workouts | Error |
| Respect locked training / recurring locked | Error |
| Unavailable days / max duration | Error |
| Max hard sessions per week | Error |
| A-race date immovable | Error |
| Fixed wrestling moved by AI | Error |
| Weekly volume increase ≤ 10–15% | Warning |
| Consecutive hard days | Warning |
| Workout step durations sum ≈ total | Error |
| Duplicate export to same provider | Error |

### Output

```csharp
public sealed record ValidationResult(
    IReadOnlyList<ValidationIssue> Errors,
    IReadOnlyList<ValidationIssue> Warnings,
    bool IsValid);
```

Run after AI response and again on user edits before approval.

---

## 28. Background jobs

Use **Hangfire** initially. All jobs must be **idempotent**.

| Job | Trigger | Purpose |
|-----|---------|---------|
| `ImportActivitiesJob` | Schedule + manual | Pull from Intervals.icu |
| `UpdateActivitiesJob` | After import | Upsert changed rows |
| `MatchActivitiesToPlannedWorkoutsJob` | After import | Planned vs actual |
| `RecalculateTrainingSummariesJob` | After import/match | Rollups |
| `SyncPlannedWorkoutsJob` | After approval | Export to Intervals.icu |
| `RetryFailedSyncJob` | Schedule | Exponential backoff |
| `RefreshTokensJob` | Schedule | Future OAuth providers |
| `GenerateWeeklySummaryJob` | Weekly | Precompute review data |

Hangfire in same `TrainingPlanner.Web` process for MVP. Split worker container later if needed.

All jobs accept `athleteId` + `correlationId`, log to `sync_logs`.

---

## 29. Synchronization and idempotency

Activity synchronization must be: incremental, idempotent, retryable, observable, safe against duplicates.

### SyncState example

```json
{
  "lastSuccessfulSyncAt": "2026-09-15T18:00:00Z",
  "activityCursor": { "page": 3, "since": "2026-06-01T00:00:00Z" },
  "workoutExportCursor": null
}
```

### Initial import flow

```
User connects Intervals.icu
  ↓
Import last 90 or 180 days
  ↓
Store normalized activities
  ↓
Create training summaries
```

### Ongoing sync flow

```
Hangfire scheduled sync
  ↓
Fetch new or updated activities
  ↓
Upsert local data
  ↓
Recalculate dependent summaries
```

Also provide **Sync now** as a manual action.

### Import upsert algorithm

1. Load batch from provider.
2. For each external activity:
   - Find link by `(provider, external_id)`.
   - If none: insert activity + link.
   - If exists: compare `external_updated_at`; update if newer; else skip.
3. Update cursor; commit transaction per batch.
4. On failure: increment `consecutive_failures`, schedule retry (1m, 5m, 15m, 1h cap).

### Rate limits

- Respect `Retry-After` header.
- Disable concurrent import per connection in Hangfire.

### Observability

Every run → `sync_logs` row + Serilog structured event + OTel span `activity.import`.

Log: import duration, number of activities imported, duplicate detection, failed API calls.

---

## 30. MVC page structure

### Main navigation

Dashboard, Calendar, Activities, Goals, Planner, Workouts, Schedule, Analytics, Integrations, Settings

### Controllers and views

| Area | Controller | Key views |
|------|------------|-----------|
| Dashboard | `DashboardController` | Index (next workout, sync, trends) |
| Calendar | `CalendarController` | Day, Week, Month (+ HTMX partials) |
| Activities | `ActivitiesController` | Index, Details |
| Goals | `GoalsController` | Index, Edit |
| Planner | `PlannerController` | Index, ProposalReview |
| Workouts | `WorkoutsController` | Templates, Editor |
| Schedule | `ScheduleController` | Recurring, Availability |
| Analytics | `AnalyticsController` | Volume, Load (post-MVP) |
| Integrations | `IntegrationsController` | Intervals.icu connect, sync status |
| Settings | `SettingsController` | Profile, zones, API keys |
| API | `ExternalActivitiesController` | GitHub Action endpoint |

### Calendar features

- Day / week / month views
- Planned workouts, completed activities, recurring training, races, rest days, unavailable days
- Planned vs actual display
- Drag and drop, quick edit
- Locked entries, optional workouts
- Sport-specific visual distinction

### HTMX usage

- Calendar drag-drop save partial
- Sync now button → status partial refresh
- Proposal review approve/reject without full reload
- Quick edit workout modal

### Dashboard

Today's training, Next workout (most important), Fixed training today, Upcoming competition, Recent training volume/load, RPE trend, Feeling trend, Sync status, AI recommendation with explanation when adapted.

**CSS:** Bootstrap 5 for MVP.

---

## 31. Project and folder structure

```
TrainingPlanner.sln
src/
  TrainingPlanner.Domain/
    Entities/
    Enums/
    ValueObjects/
    Exceptions/
  TrainingPlanner.Application/
    Abstractions/          # IActivityImportService, IAiTrainingPlanner, etc.
    Activities/
    Planning/
    Validation/
    TrainingContext/
    DTOs/                  # internal snapshots only
  TrainingPlanner.Infrastructure/
    Persistence/
      Configurations/
      Migrations/
      Repositories/
    Identity/
    Integrations/
      IntervalsIcu/
      OpenAi/
      GitHubAction/
    BackgroundJobs/
    Logging/
    Telemetry/
  TrainingPlanner.Web/
    Controllers/
    Views/
    ViewModels/
    wwwroot/
    Program.cs
tests/
  TrainingPlanner.Domain.Tests/
  TrainingPlanner.Application.Tests/
  TrainingPlanner.Integration.Tests/
docker/
  docker-compose.yml
  Dockerfile
```

### Provider abstractions (Application layer)

Small focused interfaces — do not create a gigantic generic provider interface:

- `IActivityProvider`
- `IWorkoutPublisher`
- `IExternalConnectionService`
- `IAiTrainingPlanner`
- `ITrainingSummaryService`
- `ITrainingPlanValidator`

Provider-specific DTOs remain in Infrastructure.

**Dependency rule:** Web → Infrastructure → Application → Domain.

**Registration:** extension methods `AddApplication()`, `AddInfrastructure()`, `AddWeb()`.

---

## 32. Security

### Identity

- ASP.NET Core Identity with EF stores in PostgreSQL.
- Cookie auth for MVC; API keys for external POST (separate handler).

### Secret storage

| Environment | Approach |
|-------------|----------|
| **Local dev** | .NET User Secrets + `appsettings.Development.json` (no secrets in git) |
| **Docker dev** | `.env` file (gitignored) injected via Compose |
| **Production** | Docker secrets / vault (Azure Key Vault, AWS SSM, Doppler) |

### Credentials to protect

- Intervals.icu API key / tokens
- Future Garmin tokens
- OpenAI API key
- GitHub Action authentication secret / per-athlete API keys

Do not store external credentials in plain text.

### Credential encryption

- `ExternalConnection.EncryptedCredentials` encrypted with ASP.NET Data Protection API (persist keys to volume in Docker).

### Other

- HTTPS only in production.
- CSRF on MVC forms; API key on external endpoints.
- Rate limit external API endpoint.
- Hangfire dashboard behind admin auth.
- Never log secrets or sensitive tokens.

---

## 33. Logging / observability

### Serilog

- Structured JSON to console + file/Seq in dev.
- Enrich: correlation ID (middleware), `AthleteId`, `SyncId`, `ProposalId`.

### OpenTelemetry

- Traces: HTTP (Intervals.icu, OpenAI), EF Core, Hangfire jobs.
- Metrics: `activities_imported`, `sync_duration`, `ai_proposal_duration`, `validation_failures`.

### Log events

- Provider syncs, failed API calls, AI planning requests, validation failures, workout export, import duration, duplicate detection.

Avoid logging secrets or sensitive tokens.

---

## 34. Testing strategy

| Layer | Focus | Tools |
|-------|-------|-------|
| Domain | Value objects, stress calculation edge cases | xUnit |
| Application | Normalizer, validator rules, matching, context builder | xUnit + mocks |
| Infrastructure | Intervals.icu DTO mapping, API client | xUnit |
| Integration | Repositories, migrations, sync idempotency | Testcontainers PostgreSQL |
| Web | Critical MVC flows (optional) | WebApplicationFactory |

### Required test scenarios

- Duplicate activity import → single row
- Updated Intervals.icu activity → fields updated
- Missing RPE → no error; assumed load for wrestling
- Wrestling without RPE/Feeling
- Planned workout matched on same day/sport
- Failed sync → retry increments, no partial corrupt state
- AI schema validation rejects malformed response

### AI testing

- Mock `IAiTrainingPlanner` in CI; no live GPT 5.6 calls in CI.
- Optional `[Trait("Category", "LiveAi")]` smoke test run locally.
- Record/replay sample GPT 5.6 responses as test fixtures.

---

## 35. Docker development environment

### docker-compose.yml

- `postgres:16` with volume
- `trainingplanner-web` (ASP.NET, ports 8080/8081)
- optional `seq` for logs

### Dockerfile

Multi-stage build, `dotnet publish TrainingPlanner.Web`.

### Migrations

Run on startup (dev) or separate init container (prod).

### Hangfire

Same process as web in MVP; PostgreSQL storage.

### Local workflow

```bash
docker compose up -d postgres
dotnet ef database update --project src/TrainingPlanner.Infrastructure
dotnet run --project src/TrainingPlanner.Web
```

---

## 36. Ordered implementation roadmap

| Phase | Deliverable |
|-------|-------------|
| **0** | Solution skeleton, Docker, Identity, empty DB |
| **1** | Vertical slice 1 (see §39) |
| **2** | Athlete profile + zones + sport profiles (wrestling defaults) |
| **3** | Recurring wrestling + availability + calendar expansion |
| **4** | Goals + competitions on calendar |
| **5** | Planned workout editor + steps |
| **6** | `TrainingContext` builder + summaries |
| **7** | OpenAI proposal (GPT 5.6) + validator + approval UI |
| **8** | Export planned workouts to Intervals.icu |
| **9** | Planned vs actual matching + adaptive context |
| **10** | Dashboard polish + weekly review (basic) |
| **11** | GitHub Action endpoint |
| **12** | Coach chat, workout library, analytics (post-MVP) |

---

## 37. Architectural risks

| Risk | Mitigation |
|------|------------|
| Intervals.icu API changes | Adapter isolation + contract tests |
| AI proposes invalid plans | Structured output + validator gate |
| Calendar recurrence complexity | Virtual expansion; materialize on demand |
| Duplicate activities across providers | Link table + fingerprint suggestions later |
| Hangfire in web process | Accept for MVP; extract worker if scale needed |
| Encrypted credentials on Docker restart | Persist Data Protection keys volume |
| OpenAI cost/latency | Summarized context; fast model for micro-edits |
| GPT 5.6 API availability / pricing | Configurable model ID + fallback to 4o-mini |
| Model behavior drift | Pin model version when supported; snapshot test fixtures |
| Scope creep | Strict MVP list; feature flags |

---

## 38. Decisions still required before coding

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Intervals.icu auth | API key vs OAuth | **API key** for MVP |
| 2 | CSS framework | Bootstrap vs Tailwind | **Bootstrap 5** for MVP |
| 3 | Calendar UI | FullCalendar vs custom | **FullCalendar** + HTMX partials |
| 4 | Initial import window | 90 vs 180 days | **90 days** default, user-selectable |
| 5 | Time zones | Athlete home TZ vs UTC | Store **UTC**; display in athlete TZ |
| 6 | AI model | GPT 5.6 vs older models | **GPT 5.6** primary; gpt-4o-mini fallback |
| 7 | Workout export format | ICU calendar events vs structured workout | Research ICU API during Phase 8 |
| 8 | API key for GitHub Action | Per-athlete key vs global secret | **Per-athlete** revocable key |
| 9 | Materialize recurring instances | On approval only vs pre-generate 4 weeks | **On approval / edit only** |
| 10 | Single vs multi-athlete MVP | One profile enforced | **One athlete per user** in app layer |

---

## 39. Recommended first vertical slice

**Goal:** Prove the integration boundary and local-first data model with visible user value.

### Scope

1. Create solution structure (4 projects + test project).
2. PostgreSQL + EF Core + initial migration (`athletes`, `training_activities`, `external_connections`, `external_entity_links`, `sync_states`, `sync_logs`).
3. ASP.NET Core Identity (register/login).
4. Integrations page: connect Intervals.icu API key (encrypted).
5. `IntervalsIcuActivityProvider` + `ActivityImportService`.
6. Hangfire `ImportActivitiesJob` + **Sync now** button.
7. Activities list page (table: date, sport, duration, load, RPE if present).
8. **Basic weekly calendar** view showing imported activities (read-only; no planned workouts yet).
9. Serilog + correlation ID middleware.
10. Integration test: duplicate import idempotency with Testcontainers.

### Out of slice (next)

AI planning, planned workouts, export, recurring rules, availability, matching.

### Success criteria

- User logs in, connects Intervals.icu, syncs activities, sees them in list and week calendar **without** live API calls on page load.
- Re-running sync does not duplicate activities.
- App works if Intervals.icu is unreachable (shows last sync time + cached data).

### Why this slice first

It validates the most critical architectural constraint — **provider → normalize → PostgreSQL → UI** — before investing in AI and calendar complexity. Everything else hangs off having trustworthy local activity data.

---

## Related repository context

This repository currently contains a **wrestling FIT file generator** (FitChamp) and GitHub Action for Garmin upload. That tooling can coexist with Training Planner. Future integration options:

- Wrestling activities arrive via Intervals.icu sync (Garmin → Intervals.icu → Training Planner), or
- GitHub Action POSTs directly to Training Planner API (§15).

---

*This document is the canonical architecture plan for Training Planner development. Update it as decisions are made and phases are completed.*
