# Training Planner — Product and Architecture Plan

Status: proposed architecture, before implementation  
Target stack: .NET 10, ASP.NET Core MVC, Razor Views, EF Core, PostgreSQL, ASP.NET Core Identity, HTMX, Bootstrap, HttpClientFactory, Hangfire, Serilog, OpenTelemetry, xUnit, Testcontainers, Docker

## Executive decisions

The application will be a modular monolith with four projects: Domain, Application, Infrastructure, and Web. PostgreSQL is the system of record. External fitness platforms and OpenAI are replaceable adapters; neither their DTOs nor their availability may define the core model.

The design is multi-user-safe from the start by scoping athlete data with `AthleteId`, but the MVP exposes one athlete profile per Identity user. Completed activities and planned workouts are separate. Every AI-generated change is a versioned proposal that passes deterministic validation and requires approval before it changes the calendar or is published externally.

The current repository is a small wrestling FIT generator and Garmin uploader. It should remain usable while the new solution is introduced. Its GitHub workflow can later call the authenticated ingestion endpoint, but direct Garmin integration is not part of the Training Planner MVP.

## 1. Product summary

Training Planner is a personal endurance-training planning platform that combines:

- goals, races, phases, availability, and immovable recurring sessions;
- locally persisted completed activities and subjective feedback;
- structured planned workouts and planned-versus-actual outcomes;
- adaptive, explainable AI proposals;
- deterministic safety and scheduling validation; and
- reliable import from and workout export to Intervals.icu.

Its core promise is: **show the athlete the most appropriate next workout, explain why, and keep the plan synchronized without surrendering control to AI or an external provider.**

The application is not an Intervals.icu viewer. It owns a provider-neutral training model and remains useful from its local database during an external outage.

## 2. Main user journeys

### 2.1 First-time setup

1. The user registers or signs in.
2. They create an athlete profile, timezone, sports, thresholds, preferences, and basic availability.
3. They add fixed recurring wrestling sessions and a primary goal or competition.
4. They connect Intervals.icu.
5. The application imports the configured initial window (default 90 days; optionally 180), persists activities, computes summaries, and shows sync progress.
6. The user sees imported activities in a weekly calendar and activity history.

### 2.2 Generate and approve the next week

1. The user opens Planner and asks for the next seven days.
2. The system builds a summarized `TrainingContext` from PostgreSQL.
3. OpenAI returns a structured proposal, never database mutations.
4. Deterministic validation reports blocking errors and warnings.
5. The user reviews explanations and edits, regenerates, or approves selected changes.
6. Approved workouts are stored, then queued for Intervals.icu publication.

### 2.3 Daily adaptation

1. A completed activity is imported and matched to a planned workout.
2. The user optionally adds or corrects RPE, Feeling, and notes.
3. Actual-versus-planned metrics and training summaries are recalculated.
4. If actual stress was materially different, the dashboard calls this out.
5. Any replan is a proposal; locked sessions and races remain unchanged.

### 2.4 Sync and diagnose

1. Scheduled Hangfire jobs import recent changes and publish approved workouts.
2. Integrations shows last success, current state, cursor, counts, and sanitized errors.
3. “Sync now” enqueues the same idempotent job; it does not perform provider I/O in the web request.
4. A failed run retries with backoff and can be retried manually.

### 2.5 Maintain reusable workouts

1. The user creates or duplicates a workout template.
2. They build nested warmup, interval, recovery, repeat, and cooldown steps.
3. They schedule it or ask AI to use it.
4. Provider exporters translate the internal structure and report unsupported constructs before publishing.

### 2.6 Weekly review and coach chat

1. The system computes a factual weekly review from local data.
2. AI may summarize it and recommend adjustments.
3. Chat answers questions from the current context.
4. Any requested calendar change becomes a visible proposal, not a silent tool action.

## 3. Functional requirements

### Identity and athlete setup

- Register, log in, log out, reset password, and manage account.
- One athlete profile per user in the MVP; retain explicit `AthleteId` ownership on all athlete data.
- Configure timezone, sports, physiological thresholds/zones, preferences, and planning limits.

### Activities

- Connect Intervals.icu and import activities incrementally.
- Persist normalized activities with nullable sport-specific metrics.
- Browse/filter activity history and edit local feedback.
- Show source links and sync freshness without exposing provider DTOs.
- Accept idempotent externally submitted activities through a separate machine-authenticated API.

### Calendar and schedule

- Day, week, and month presentations of planned workouts, completed activities, races, recurring training, rest days, and unavailable periods.
- Sport/status visual treatment, planned-versus-actual indicators, quick edit, and lock/optional controls.
- Drag/drop rescheduling with server-side conflict validation and optimistic concurrency.
- Recurring rules with date-bounded exceptions rather than pre-creating an unbounded row per occurrence.

### Planning

- Goals, competitions, phases, availability, and workout library CRUD.
- Generate, regenerate, shorten, ease, harden, convert, and replan through AI proposals.
- Validate proposals, show errors/warnings, require approval, and preserve explanation/provenance.
- Publish only approved workouts to Intervals.icu.

### Analysis

- Training volume/load summaries, RPE and Feeling trends, weekly review, and planned-versus-actual comparison.
- Dashboard focused on next workout, rationale, recent stress, upcoming race, and sync status.

## 4. Non-functional requirements

- **Correctness:** all timestamps are stored as UTC instants; athlete timezone is used for calendar dates and recurrence. No fabricated metrics.
- **Availability:** reads use PostgreSQL, not live provider calls. Provider outages degrade sync, not calendar/history.
- **Idempotency:** repeated imports, publications, callbacks, manual sync clicks, and job retries produce the same state.
- **Security:** least privilege, anti-forgery for browser mutations, machine auth for ingestion, encrypted integration secrets, and no secrets/health details in logs or AI input.
- **Performance:** typical dashboard/week page under 500 ms at the server after warm-up; slow provider and AI work is asynchronous. This is an initial target to verify, not an SLA.
- **Accessibility:** semantic HTML, keyboard-accessible calendar alternatives, clear status text in addition to color, and WCAG 2.2 AA as the target.
- **Observability:** traces, structured logs, metrics, correlation IDs, and user-visible sync diagnostics.
- **Maintainability:** nullable reference types, analyzers, small use-case-oriented services, migrations in Infrastructure, and no provider references from Domain/Application contracts.
- **Portability:** one Docker Compose development setup and Linux container deployment.
- **Privacy:** minimize data sent to AI, define retention, support export/deletion, and avoid medical claims.

**Decision:** use a modular monolith. It gives atomic database transactions, simple deployment, and clear code boundaries. Microservices are an unreasonable operational cost for the MVP; modules can be extracted only if actual scaling or team boundaries require it.

## 5. MVP scope

The MVP includes:

- Identity login and one athlete profile per user;
- PostgreSQL and EF Core migrations;
- Intervals.icu connection, initial/incremental activity import, local activity history, sync status, and “Sync now”;
- weekly calendar with completed activities, planned workouts, competitions, availability, and recurring wrestling;
- goals and basic Base/Build/Peak/Taper/Recovery phase selection;
- structured workouts and a small workout-template library;
- optional RPE and Feeling capture;
- AI generation of the next seven days from a summarized context;
- deterministic validation, proposal review, and explicit approval;
- local storage and idempotent export of approved workouts to Intervals.icu;
- planned-versus-actual matching and use of the result in the next context; and
- basic dashboard and weekly factual summary.

Limit the MVP to the sports and fields required by the internal model, even if Intervals.icu exposes more. Preserve unmapped diagnostics only where useful; do not model every provider field.

## 6. Features excluded from MVP

- Direct Garmin or Zwift APIs and FIT workout export.
- Weather, nutrition, equipment maintenance, medical readiness, and advanced race prediction.
- Native mobile applications.
- Coach/athlete organizations, invitations, billing, and multi-athlete dashboards.
- Automatic plan approval or direct AI-to-provider writes.
- Full wellness import, route planning, social features, and real-time telemetry.
- Automatic cross-provider duplicate merges without user review.
- Highly specialized periodization algorithms for every sport.

The provider interfaces and athlete ownership keys keep later additions possible without building unused framework now.

## 7. Domain model

### Core entities and value concepts

- `AthleteProfile`: timezone, preferences, planning limits, profile version.
- `SportProfile`: sport-specific FTP, heart-rate thresholds, preferred target type, and defaults.
- `TrainingZone`: zone system, ordinal, lower/upper bound, unit, and effective dates.
- `Goal`: desired outcome and priority.
- `Competition`: immutable event date unless explicitly edited; A/B/C priority.
- `TrainingPhase`: date-bounded phase influencing plan generation.
- `AvailabilityRule` / `AvailabilityException`: normal capacity and temporary override.
- `RecurringTrainingRule` / `RecurringTrainingException`: fixed schedule and occurrence override.
- `TrainingActivity`: provider-independent completed activity.
- `ActivityFeedback`: optional RPE, normalized Feeling, notes, and source.
- `PlannedWorkout`: scheduled intent, status, load/intensity expectation, lock state, and structured steps.
- `WorkoutCompletion`: link and comparison between a plan and one or more actual activities.
- `WorkoutTemplate`: reusable workout definition.
- `ExternalConnection`: provider connection metadata and encrypted credential payload reference.
- `ActivitySourceLink` and `WorkoutPublication`: strongly typed external identity/sync records.
- `SyncState` / `SyncRun`: cursor and operational history.
- `AiPlanningProposal`: immutable context/prompt/output metadata plus review status.
- `ProposalWorkout`: typed candidate change belonging to a proposal.

### TrainingActivity

Recommended fields:

```text
Id, AthleteId
Sport, ActivityType, Title
StartTimeUtc, EndTimeUtc, LocalDate, TimeZoneId
MovingDuration, ElapsedDuration
DistanceMeters?, ElevationGainMeters?
AverageHeartRateBpm?, MaximumHeartRateBpm?
AveragePowerWatts?, NormalizedPowerWatts?, AverageCadenceRpm?
CaloriesKcal?
ProviderTrainingLoad?, CalculatedTrainingLoad?, EffectiveTrainingLoad?
TrainingEffect?
Notes?
ImportedAtUtc, SourceUpdatedAtUtc?, UpdatedAtUtc
RowVersion
```

`LocalDate` is a denormalized calendar key derived using the athlete timezone at ingestion. It makes calendar queries and date matching deterministic even if the profile timezone changes later. Durations and measurements use explicit units in names. Metrics that do not apply remain `NULL`.

RPE and Feeling are separated into `ActivityFeedback` because they can be edited locally, may have provenance, and should not be overwritten by a later provider update. A one-to-one current feedback row is enough for MVP; add history only if audit requirements emerge.

**Alternative:** put all feedback directly on `TrainingActivity`. This is simpler but complicates precedence between provider and user-entered values. Separation is a small cost with useful semantics.

## 8. Aggregate boundaries

Use transactional boundaries, not large object graphs:

1. **Athlete configuration:** `AthleteProfile` root with sport profiles/preferences. Zones may be updated through the same application use case but need not be loaded for every profile mutation.
2. **Training activity:** `TrainingActivity` root; feedback and source links are changed through activity use cases. Import upserts one activity at a time in a transaction and advances the cursor only after the batch commits.
3. **Planned workout:** `PlannedWorkout` root owns steps and completion links. Step invariants are validated before save.
4. **Workout template:** independent root owning template steps.
5. **Schedule rule:** each recurring or availability rule is its own root; exceptions reference exactly one rule.
6. **Goal/competition/phase:** small independent roots scoped to the athlete.
7. **External connection:** connection root; sync state and runs are operational records, not a giant integration aggregate.
8. **AI proposal:** proposal root owns immutable proposed operations and review/approval state. Approval calls domain/application use cases for affected workouts in one transaction where practical.

Do not make `AthleteProfile` a parent aggregate containing all athlete data. That would create excessive loading and concurrency contention. Cross-aggregate rules belong in application services and `ITrainingPlanValidator`.

## 9. Entity relationships

```text
AspNetUser 1 ── 1 AthleteProfile
AthleteProfile 1 ── * SportProfile 1 ── * TrainingZone
AthleteProfile 1 ── * Goal
AthleteProfile 1 ── * Competition
AthleteProfile 1 ── * TrainingPhase
AthleteProfile 1 ── * AvailabilityRule 1 ── * AvailabilityException
AthleteProfile 1 ── * RecurringTrainingRule 1 ── * RecurringTrainingException
AthleteProfile 1 ── * TrainingActivity 1 ── 0..1 ActivityFeedback
TrainingActivity 1 ── * ActivitySourceLink
AthleteProfile 1 ── * PlannedWorkout 1 ── * WorkoutStep
PlannedWorkout 1 ── * WorkoutCompletion * ── 1 TrainingActivity
PlannedWorkout 1 ── * WorkoutPublication
AthleteProfile 1 ── * WorkoutTemplate 1 ── * WorkoutTemplateStep
AthleteProfile 1 ── * ExternalConnection 1 ── * SyncState / SyncRun
AthleteProfile 1 ── * AiPlanningProposal 1 ── * ProposalWorkout
```

A completion join supports a brick/multisport plan completed by multiple activities, while a single activity should normally match at most one planned workout. Enforce the latter for active automatic links; permit an explicit override if future use cases prove it necessary.

## 10. PostgreSQL schema proposal

Use `uuid` primary keys (UUIDv7 generated in the application), `timestamptz` for instants, `date`/`time` for local schedules, `interval` or integer seconds consistently for duration, numeric types with explicit units, snake_case database naming, and UTC audit columns. Use string-backed constrained enums or PostgreSQL enums only after values stabilize; MVP recommendation is small integers mapped from domain enums plus check constraints.

### Principal tables

| Table | Important columns | Constraints/indexes |
|---|---|---|
| `athlete_profiles` | `id`, `user_id`, `time_zone_id`, preferences, limits, `row_version` | unique `user_id` |
| `sport_profiles` | `id`, `athlete_id`, `sport`, thresholds/defaults | unique (`athlete_id`,`sport`) |
| `training_zones` | `sport_profile_id`, `system`, `ordinal`, bounds/unit, effective dates | unique (`sport_profile_id`,`system`,`ordinal`,`effective_from`) |
| `goals` | `athlete_id`, type, sport, priority, target date/value/unit, active/archived | index (`athlete_id`,`active`,`target_date`) |
| `competitions` | `athlete_id`, name, local date/time, sport, priority, target | index (`athlete_id`,`event_date`) |
| `training_phases` | `athlete_id`, type, start/end date, goal id? | exclusion/validation against unwanted overlap; index date range |
| `availability_rules` | weekday, local start/end or max duration, permitted sports/mode, effective dates | index (`athlete_id`,`weekday`,`valid_from`) |
| `availability_exceptions` | rule id?, date/range, replacement capacity, reason/type | index (`athlete_id`,`start_date`,`end_date`) |
| `recurring_training_rules` | weekday, local time, duration, timezone, sport, lock/move flags, defaults, effective dates | index (`athlete_id`,`weekday`,`valid_from`) |
| `recurring_training_exceptions` | rule id, occurrence date, action, replacement fields | unique (`rule_id`,`occurrence_date`) |
| `training_activities` | normalized fields described above | index (`athlete_id`,`start_time_utc`); index (`athlete_id`,`local_date`); index (`athlete_id`,`sport`,`start_time_utc`) |
| `activity_feedback` | activity id, rpe?, feeling?, notes?, source, updated | unique `activity_id`; checks RPE range |
| `activity_source_links` | activity id, connection id, provider, external id, provider revision, source updated, payload hash, optional sanitized raw payload, last synced, fingerprint, missing/deleted marker | unique (`connection_id`,`external_id`); index fingerprint |
| `planned_workouts` | athlete/date/times, sport, status, intensity/load, lock/optional, origin, proposal id?, version | index (`athlete_id`,`scheduled_date`); concurrency token |
| `workout_steps` | workout id, parent step id?, order, type, duration fields, target fields, repetitions? | unique (`workout_id`,`parent_step_id`,`sort_order`); checks by step type |
| `workout_templates` | athlete id, name, sport, description, version | unique name per athlete, or permit duplicates with a normal index |
| `workout_template_steps` | same structural columns as workout steps | same ordering checks |
| `workout_completions` | workout id, activity id, method, confidence, metrics, confirmed | unique (`workout_id`,`activity_id`); partial unique activity for active match |
| `external_connections` | athlete, provider, status, provider account id, encrypted secret reference/payload, last error | unique (`athlete_id`,`provider`,`provider_account_id`) |
| `workout_publications` | workout, connection, external id?, hash, status, remote version, timestamps | unique (`connection_id`,`workout_id`); unique (`connection_id`,`external_id`) where not null |
| `sync_states` | connection, stream, cursor?, watermark?, overlap, last success/attempt | unique (`connection_id`,`stream`) |
| `sync_runs` | connection, stream, correlation id, state, counts, timings, sanitized error | index (`connection_id`,`started_at desc`) |
| `ai_planning_proposals` | athlete, status, scope, context snapshot/hash/version, model, prompt/schema versions, raw structured result, validation, timestamps | index (`athlete_id`,`created_at desc`) |
| `proposal_workouts` | proposal, operation, target workout id?, typed candidate payload/order | index `proposal_id` |
| `training_daily_summaries` | athlete/date/sport, duration/load/RPE counts | unique (`athlete_id`,`date`,`sport`) |
| `training_weekly_summaries` | athlete/week start/sport, planned/actual metrics | unique (`athlete_id`,`week_start`,`sport`) |
| `outbox_messages` | message type, aggregate id/version, payload, available/processed times, attempts | unique idempotency key; index (`processed_at`,`available_at`) |

Add `athlete_id` to operational child rows where it materially improves row ownership checks and query plans, but do not duplicate it everywhere without a constraint strategy. All user-facing queries must be athlete-scoped; add integration tests that attempt cross-athlete access.

Use JSONB narrowly:

- acceptable for immutable AI context/output snapshots, sanitized provider diagnostic payloads, and flexible non-secret preferences;
- not acceptable as the primary representation of activities, workout steps, sync state, or query-critical fields.

Keeping a sanitized source payload is optional but useful for replaying mappings and diagnosing provider changes. Encrypt or omit it when it contains sensitive fields, enforce retention, and use the payload checksum/revision—not JSON queries—for change detection.

**External link decision:** use strongly typed `activity_source_links` and `workout_publications`, not one polymorphic `external_entity_links` table. Typed foreign keys preserve referential integrity and allow different sync semantics. A generic table is shorter initially but cannot enforce that `internal_entity_id` points to the declared entity and tends to become a catch-all.

## 11. Activity import architecture

### Contract

Place a provider-neutral port and records in Application:

```csharp
public interface IActivitySource
{
    string ProviderKey { get; }

    Task<ActivityChangePage> GetChangesAsync(
        ActivityChangeRequest request,
        CancellationToken cancellationToken);
}

public sealed record ActivityChangeRequest(
    DateTimeOffset ChangedSince,
    DateTimeOffset RangeStart,
    DateTimeOffset RangeEnd,
    string? Cursor,
    int PageSize);

public sealed record ActivityChangePage(
    IReadOnlyList<ImportedActivity> Activities,
    string? NextCursor,
    bool HasMore,
    DateTimeOffset ProviderWatermark);
```

`ImportedActivity` is an application ingestion contract with normalized units and optional values. Intervals-specific JSON DTOs and mapping stay in Infrastructure. The provider returns data; an application orchestrator owns normalization validation, duplicate resolution, persistence, summaries, and cursor advancement.

This paged/cursor-aware contract is preferable to returning an unbounded collection because it supports rate limits, retries, partial provider APIs, and large initial imports. If Intervals.icu only offers time windows, the adapter implements a synthetic cursor from window/watermark and page position.

### Pipeline

```text
Hangfire/manual enqueue
  → acquire per-connection/stream lock
  → read cursor and overlap window
  → IActivitySource.GetChangesAsync
  → provider DTO mapping
  → normalized contract validation
  → resolve source identity / duplicate candidates
  → transactional activity + source-link upsert
  → write follow-up outbox messages
  → commit page, cursor, and outbox atomically
  → dispatch matching and summary jobs
```

Import a small overlap window (for example seven days) on every incremental run because providers can update older records. Periodically run a wider reconciliation window. The overlap is configurable and does not replace a provider “updated since” cursor when available.

Do not place EF entities in provider adapters. Do not let the provider call repositories directly. This keeps mapping tests and import idempotency tests independent.

## 12. Intervals.icu integration

### Connection

The MVP connection stores athlete/account identifier and an encrypted API credential using the authentication mechanism Intervals.icu supports. Do not design token refresh unless the selected Intervals.icu authorization flow actually issues refreshable tokens. Verify current endpoints, scopes, update semantics, and limits against official API documentation during implementation.

### Import adapter

`IntervalsIcuActivitySource` uses a named/typed HttpClient:

- base address and timeout from configuration;
- authentication added by a delegating handler without logging it;
- resilience handler for transient network errors, 408/429/5xx, exponential backoff with jitter, and `Retry-After`;
- DTOs internal to `Infrastructure/Integrations/IntervalsIcu/Activities`;
- explicit mapping for sport, timestamps, metric units, RPE, Feeling, and provider load;
- unknown sport maps to `Other` with a diagnostic, never a failed whole page.

The adapter must distinguish transient errors, authentication failures, rate limiting, malformed responses, and unsupported values. Application-level sync status converts these to safe user messages.

### Workout export adapter

`IntervalsIcuWorkoutPublisher : IWorkoutPublisher` translates the internal workout tree into Intervals.icu’s current workout representation. Before sending:

1. validate locally and for provider capabilities;
2. compute a canonical content hash;
3. inspect `workout_publications`;
4. create only if no external ID exists;
5. update by external ID when content changed;
6. no-op when the last published hash matches.

Store remote ID/version/updated timestamp and last published hash. On remote changes since the last known version, mark a conflict and require user choice; never blindly overwrite. Cancellation should default to removing/cancelling the remote event only when the user confirms and the local publication owns it. A soft-cancel with an explicit later cleanup job is safer than coupling a local transaction to remote deletion.

**Alternative:** treat Intervals.icu as the source of truth for planned workouts. Rejected because offline behavior, AI approval, provider portability, and conflict handling all require a local canonical plan.

## 13. Future Zwift integration

Add `ZwiftActivitySource` in Infrastructure and register it by provider key. It maps Zwift DTOs into the same `ImportedActivity` contract and uses the same import orchestrator, source-link, matching, summary, and calendar paths.

If direct Zwift workout publication becomes available, add a separate `IWorkoutPublisher`; if only ZWO download is practical, implement an exporter rather than pretending it is a remote publisher.

No Domain, calendar, analytics, AI context, or completion-matching changes should be required. Some provider capability metadata may be added in Application:

```text
supports activity updates
supports workout create/update/delete
supported sports, step types, and targets
```

Do not implement a generic plugin framework or load assemblies dynamically. Dependency-injection registration is sufficient.

## 14. Future Garmin integration

Garmin remains an Infrastructure adapter. Potential adapters are deliberately separate:

- `GarminActivitySource`;
- `GarminWorkoutPublisher`;
- FIT file importer/exporter.

Garmin access constraints, approval requirements, and field semantics must be verified before selecting an API. Existing repository scripts that generate/upload a wrestling FIT activity are not a supported direct Garmin integration and should not be coupled to the domain.

If Garmin and Intervals import the same activity, each creates a source link. Exact provider IDs prevent intra-provider duplicates; cross-provider fingerprinting proposes a merge onto one canonical `TrainingActivity`.

## 15. GitHub Action integration

Expose a versioned machine endpoint:

```http
POST /api/v1/external-activities
Authorization: Bearer <opaque scoped credential>
Idempotency-Key: <optional request key>
Content-Type: application/json
```

Required payload fields:

```json
{
  "source": "github-wrestling",
  "externalActivityId": "run-or-domain-stable-id",
  "sport": "Wrestling",
  "activityType": "Training",
  "startTime": "2026-09-15T19:00:00+02:00",
  "durationSeconds": 5400,
  "title": "Wrestling",
  "trainingLoad": 75,
  "rpe": null,
  "feeling": null
}
```

Return `201 Created` on first creation and `200 OK` with the same internal ID on an idempotent replay/update. Require a stable external ID, validate timestamp/duration/ranges, cap body size, and rate-limit by credential.

Recommended machine authentication is a random 256-bit opaque API credential. Store only a keyed hash plus credential ID, athlete scope, expiration, and last-used timestamp. Display it once. This is simpler and safer for one GitHub Action than building OAuth client credentials. Rotate by overlapping old/new credentials briefly. A signed HMAC request is a reasonable alternative when replay-window protection is needed, but introduces clock and canonicalization complexity.

The endpoint invokes the same normalized ingestion application service as provider imports, with a synthetic external connection/source link. It does not require RPE or Feeling and applies configured wrestling default planning load only if the sender provides no objective/provider load. It must never fabricate RPE.

## 16. Recurring training design

`RecurringTrainingRule` contains:

```text
AthleteId, Name, Sport
Weekday, LocalStartTime, Duration, TimeZoneId
ValidFrom, ValidUntil?
Locked, AiMayMove, DefaultIntensity, DefaultPlanningLoad?
RpeRequired, FeelingRequired
```

`RecurringTrainingException` identifies (`RuleId`, `OccurrenceDate`) and has an action:

- `Cancelled`;
- `Moved` with replacement date/time;
- `Modified` with replacement duration/intensity/load;
- `Replaced` for competition/special training.

For weekly MVP recurrence, a weekday rule is clearer than a full RFC 5545 engine. Generate occurrences for the requested calendar/context range in an application query service. Materialize a `PlannedWorkout` only when the user edits an occurrence into a workout, approves a plan around it, or completion tracking requires a durable item. Keep `OriginRecurringRuleId` and occurrence date when materialized.

This avoids hundreds of future rows while preserving stable exceptions. A general RRULE library is a reasonable later alternative for biweekly/custom patterns, but DST and exception semantics make it unnecessary MVP complexity.

Recurring rules retain local wall-clock time across daylight-saving changes. Define behavior for ambiguous/nonexistent local times and test it. Noda Time is the recommended focused dependency for IANA timezone and DST correctness; `TimeZoneInfo` is a reasonable no-dependency alternative only if the team implements and thoroughly tests those edge cases.

Wrestling defaults represent **assumed load**, not measured load. An imported completed session can replace the assumed load with better objective/provider/manual evidence.

## 17. Availability design

Availability describes capacity; recurring training consumes capacity. Keep them separate.

An `AvailabilityRule` applies to weekday plus effective dates and supports:

- one or more local available windows;
- maximum total duration;
- allowed mode (Any, Indoor, Outdoor);
- allowed sports or “wrestling only”;
- optional notes.

For the MVP, either permit one rule row per window or a parent rule with child windows. Prefer child `availability_windows` if split morning/evening availability is required at launch; otherwise a single nullable start/end and max duration is enough.

`AvailabilityException` is an athlete/date range override with unavailable, replacement windows/max duration, and reason (work, family, vacation, other). Exceptions take precedence over normal rules; more specific single-day exceptions beat ranges. Reject ambiguous overlapping replacement exceptions rather than inventing priority logic.

The context builder converts rules, exceptions, existing plans, and recurring training into daily remaining capacity. The validator uses the same resolved schedule service so AI and deterministic rules cannot disagree.

## 18. Goal and competition design

Keep `Goal` and `Competition` separate:

- a goal can be non-event-based (FTP, pace, weight, volume, base fitness);
- a competition is a calendar constraint and may be linked to one or more goals.

`Goal` stores type, sport, priority, target date, value and unit, current value and provenance, status, and description. Do not use one untyped string for target values. Use nullable numeric value + unit for MVP and typed supplemental fields only when required.

`Competition` stores date/time, sport, A/B/C priority, target, notes, and lock semantics. A-races are always validator-protected from AI move/delete. B/C events may still only be changed by an explicit user action; “AI may adjust training around it” does not imply it may move the event.

Training phases are athlete/date ranges with `Base`, `Build`, `Specialization`, `Peak`, `Taper`, and `Recovery` types, optionally tied to a primary goal. Start with manual phases and validator checks for overlap. Automatic periodization can propose phases later.

## 19. Planned workout model

`PlannedWorkout` contains:

```text
Id, AthleteId, Title, Description, Sport
ScheduledDate, StartTime?, TimeZoneId, PlannedDuration
Status: Planned/Completed/PartiallyCompleted/Skipped/Cancelled
IntensityCategory, ExpectedRpe?, PlannedLoad?
IndoorOutdoorPreference, Optional, Locked
AiMayMove, Origin, TemplateId?, ProposalId?
CreatedAtUtc, UpdatedAtUtc, RowVersion
```

Status is explicit, not inferred only from dates. Completion matching suggests or changes status according to deterministic thresholds, with user override retained.

Store planned workouts and actual activities separately because intent and reality differ. Do not mutate planned duration/load to actual values. `WorkoutCompletion` captures the comparison.

Drag/drop sends the workout ID, expected row version, and new local date/time. The server authorizes ownership, validates constraints, updates atomically, and returns the refreshed calendar fragment through HTMX. Locked items require an explicit unlock/edit flow.

## 20. Workout step model

Use an ordered tree represented by adjacency:

```text
WorkoutStep
  Id, WorkoutId, ParentStepId?, SortOrder
  StepType: Warmup/Steady/Interval/Recovery/Repeat/Cooldown/Open
  Name?
  DurationType: Time/Distance/Open
  DurationSeconds?, DistanceMeters?
  TargetType: None/HeartRateZone/HeartRateBpm/PowerZone/Watts/
              PercentFtp/Pace/Cadence/Rpe/FreeRide
  TargetLower?, TargetUpper?, TargetUnit?
  Repetitions?     // Repeat only
```

Repeat steps own child steps. Non-repeat nested children are invalid. Leaf steps require compatible duration/target fields. Warmup/cooldown may use ranges; open steps may omit duration. The workout’s planned duration is derived from steps where fully determined, with an optional explicit duration only for unstructured workouts.

Use the same domain value model for templates and scheduled workouts but separate persistence tables to avoid scheduled workouts changing when a template is edited. Scheduling copies a versioned template snapshot.

**Alternative:** store the tree as JSONB. That simplifies persistence but weakens constraints, migrations, querying, and incremental editing. Relational adjacency is suitable for the expected small trees and EF Core.

## 21. Planned vs actual matching

Matching runs after import and can be manually corrected.

### Candidate generation

Filter by athlete, compatible sport, and a configurable time window around the planned start/date. Never compare across athletes. Exclude already confirmed matches.

### Scoring

Use deterministic weighted features:

- same local date and start-time proximity;
- sport compatibility;
- duration similarity;
- title/type hint;
- expected versus actual load;
- source-provided planned-workout reference if available.

Create an automatic match only above a high threshold with a clear margin over the second candidate. Create a suggested match for medium confidence; leave low confidence unmatched. Store method, score, feature contributions, and whether confirmed.

### Comparison

Store or derive:

- planned/actual duration and ratio;
- planned/actual load and ratio;
- expected/actual RPE delta;
- intensity comparison;
- completion percentage;
- completion state and notes.

An activity may satisfy one planned workout by default. A brick workout may link multiple activities; model this explicitly instead of weakening every uniqueness rule silently.

Do not use AI for basic matching in the MVP. Deterministic matching is cheaper, reproducible, testable, and explainable.

## 22. RPE / Feeling handling

Use domain scales:

- RPE: nullable integer 1–10 with check constraint;
- Feeling: nullable enum `VeryPoor`, `Poor`, `Normal`, `Good`, `VeryGood`.

Provider adapters normalize their scale explicitly and retain mapping tests. Unknown/out-of-range values become null plus a sanitized mapping diagnostic; they do not fail the activity.

Feedback precedence:

1. user-entered value;
2. latest supported provider value;
3. absent.

A later sync must not overwrite user-entered feedback. Store provenance (`User`, `Provider`, `ExternalSubmission`) and update timestamp. Missing values are semantically “unknown,” not zero or normal.

Wrestling can have both values absent. `RpeRequired` and `FeelingRequired` are UI preferences only; they must not make ingestion invalid.

## 23. Training load model

Represent load as an evidence-based selection:

1. **Objective calculated load:** from power/HR/pace when prerequisites and algorithms are valid.
2. **Provider load:** imported, with provider and method provenance.
3. **Subjective load:** session-RPE (`duration minutes × RPE`) where RPE exists, normalized for display/comparison.
4. **Assumed load:** configured recurring/manual default, such as wrestling 75.

Store available component values rather than collapsing all provenance. `EffectiveTrainingLoad` is selected by a versioned `TrainingLoadPolicy` with method and confidence:

```text
value, method, algorithmVersion, confidence, calculatedAt
```

For MVP, prefer a trusted provider load, then a supported local objective calculation, then session-RPE, then configured assumed load. The exact order is a product decision to validate against Intervals.icu semantics; never add incompatible load scales as if they were identical.

Daily/weekly summaries aggregate effective load by sport and total. Also retain duration because mixed-sport load numbers are approximations. Later acute/chronic trends can be computed from daily summaries, but avoid presenting a single “readiness” score as medical truth.

**Alternative:** recalculate everything from raw streams. The MVP does not import second-by-second streams and does not need that storage/algorithm complexity.

## 24. TrainingContext

`TrainingContext` is a versioned Application DTO assembled only from authorized PostgreSQL data and calculated summaries:

```text
ContextVersion, GeneratedAtUtc, AthleteTimeZone
AthleteProfileSummary
SportProfilesAndZones
ActiveGoals
UpcomingCompetitions
CurrentAndUpcomingTrainingPhase
PlanningHorizon
ResolvedDailyAvailability
FixedTrainingOccurrences
ExistingPlannedWorkouts
RecentActivitySummary (7/28/84-day windows)
DailyAndWeeklyLoadSummary
RpeTrend and FeelingTrend with sample counts/missingness
RecentNotableActivities (small capped list)
RecentPlannedVsActualOutcomes
ConstraintsAndPreferences
UserInstruction
```

Summaries must include denominators and missing-data indicators; “average RPE 5” based on one of ten activities is materially different from complete feedback. Include only a bounded set of notable/recent activity records, not hundreds of raw activities.

Build context through `ITrainingContextBuilder`, with one canonical resolved-availability/schedule implementation shared with validation. Serialize an immutable redacted snapshot and hash on each proposal so the recommendation can be reproduced. A new plan request builds a fresh context; chat can use a short-lived context reference plus conversation history.

## 25. OpenAI integration

`IAiTrainingPlanner` is an Application port. `OpenAiTrainingPlanner` in Infrastructure uses a named HttpClient or the supported OpenAI .NET SDK configured through HttpClientFactory. Domain and Application do not reference OpenAI types.

Flow:

```text
build context → persist Pending proposal
→ enqueue/execute AI request
→ require strict structured response
→ deserialize and schema/domain-shape validate
→ deterministic TrainingPlanValidator
→ persist Proposed/Invalid result
→ user review/edit
→ validate again
→ approve transactionally
→ enqueue publication
```

Recommended controls:

- pin an explicit model configuration; do not silently change models;
- version system prompt, context, and output schema;
- set bounded output and timeout;
- retry only safe transient failures and rate limits with jitter;
- use a request/correlation ID and idempotency key where supported;
- redact secrets, external IDs not needed for planning, free-text sensitive details, and Identity data;
- log metadata, duration, token counts/cost where available, and outcome—not full prompts by default;
- store the exact redacted context and structured response for proposal audit/expiry;
- reject extra/unknown critical fields and all invalid enum/range values.

AI does not receive repositories, provider clients, or database tools. It cannot approve, persist workouts, or call Intervals.icu.

Keep immutable, semantically versioned prompt and JSON Schema artifacts in source control rather than anonymous inline strings. Store their content hashes with each run. Explanations should be short rationale and evidence references; do not request or expose hidden chain-of-thought.

Transport retries and plan repair are separate. After a schema-valid response fails semantic validation, the product may offer one bounded repair attempt using the same immutable context and machine-readable validation errors. Validate the repaired proposal from scratch and stop after one attempt; never relax constraints or loop automatically.

## 26. AI structured output proposal

Use one operation envelope that can represent adding, changing, moving, or cancelling candidate workouts:

```json
{
  "schemaVersion": "1.0",
  "scope": {
    "from": "2026-09-21",
    "to": "2026-09-27"
  },
  "summary": "A lower-load week around two fixed wrestling sessions.",
  "operations": [
    {
      "operation": "add",
      "clientOperationId": "op-1",
      "targetWorkoutId": null,
      "workout": {
        "date": "2026-09-23",
        "startTime": null,
        "title": "Recovery spin",
        "sport": "Cycling",
        "plannedDurationSeconds": 2700,
        "intensity": "Recovery",
        "expectedRpe": 2,
        "plannedLoad": 20,
        "optional": false,
        "indoorOutdoor": "Either",
        "steps": [
          {
            "stepType": "Steady",
            "durationType": "Time",
            "durationSeconds": 2700,
            "targetType": "PowerZone",
            "targetLower": 1,
            "targetUpper": 1,
            "children": []
          }
        ]
      },
      "rationale": {
        "summary": "Recovery follows a harder-than-planned ride.",
        "factors": [
          {
            "code": "ACTUAL_RPE_ABOVE_EXPECTED",
            "statement": "The previous ride was 3 RPE points above expected.",
            "contextReference": "plannedActual:2026-09-20"
          }
        ]
      }
    }
  ],
  "assumptions": [],
  "warnings": []
}
```

IDs reference items present in the context; explanations use controlled reason codes plus human-readable text. The server never trusts AI-provided athlete IDs, lock states, status, external IDs, or audit fields.

Persist a typed proposal representation for review and immutable JSON snapshots for reproducibility. On approval, translate operations to commands after reloading current state and checking proposal staleness. If relevant rows/context changed, revalidate and require confirmation or regeneration.

## 27. Training plan validation

`ITrainingPlanValidator` returns structured results:

```text
Severity: Error or Warning
Code
Message
AffectedDate / WorkoutId / OperationId
SuggestedResolution?
```

MVP blocking errors:

- overlapping workouts beyond explicitly allowed overlap;
- mutation/move of locked recurring training or an A-race;
- workout outside resolved availability or over daily max duration;
- invalid/missing step fields, repeat count, or inconsistent total duration;
- invalid physiological targets against athlete profile;
- duplicate operation or duplicate scheduled workout identity;
- stale proposal targeting a changed/deleted workout;
- unauthorized athlete/entity reference.

MVP warnings requiring acknowledgement:

- maximum hard sessions per week exceeded;
- excessive consecutive hard days;
- weekly duration/load increase above configured threshold;
- competition proximity or taper conflict;
- optional workout causes availability overage;
- missing threshold needed for the chosen target;
- significant planned-versus-actual stress mismatch.

Validation occurs after AI response, after user edits, and immediately before approval. Publication adds provider-capability validation. Use rules as small classes grouped by plan/workout/publication, but avoid a generic rules engine. Plain services are easier to debug.

Warnings are not silently ignored: approval records acknowledged warning codes. Error overrides should be exceptional, user-initiated, and audited; locked/A-race/authorization invariants should not be overrideable by AI.

## 28. Background jobs

Use Hangfire with PostgreSQL storage in a separate schema. Jobs receive stable IDs, not entity objects or credentials.

| Job | Trigger | Responsibility |
|---|---|---|
| `ImportActivitiesJob` | connect/manual/schedule | run paged incremental import |
| `MatchActivitiesJob` | after changed imports | propose/confirm deterministic matches |
| `RecalculateTrainingSummariesJob` | after affected dates change | upsert daily/weekly summaries |
| `PublishPlannedWorkoutsJob` | after approval/manual retry | idempotent create/update/cancel |
| `ReconcileExternalWorkoutsJob` | periodic | detect remote drift/conflicts |
| `GenerateWeeklySummaryJob` | weekly/on demand | factual summary; optional AI narrative |
| `RefreshTokensJob` | only for providers requiring it | refresh before expiry |
| Hangfire retries | failures | replace a custom generic retry job |

Do not create both `ImportActivitiesJob` and `UpdateActivitiesJob` if they invoke the same use case; initial versus incremental is an input mode. Likewise, Hangfire already handles retries, so `RetryFailedSyncJob` is only needed if business state requires manual requeue.

Apply per-athlete/connection/stream concurrency control. Hangfire’s job uniqueness alone is insufficient; use a distributed lock or PostgreSQL advisory lock plus idempotent persistence. Keep jobs thin and call Application use cases.

Use the small transactional outbox above only at reliability boundaries where committing business state and scheduling follow-up work must be atomic—for example import-to-summary/matching and approval-to-publication. A dispatcher submits outbox records to Hangfire and marks them processed idempotently. This is not a service bus or event-sourcing design; periodic reconciliation remains the safety net.

## 29. Synchronization and idempotency

### Import identity and duplicates

1. Exact uniqueness: (`ExternalConnectionId`, `ExternalId`) in `activity_source_links`.
2. Stable normalized fingerprint candidate: athlete + sport family + rounded start instant + duration/distance tolerances.
3. Cross-provider candidate scoring; auto-link only at exceptionally high confidence, otherwise request user confirmation.
4. Never delete one activity merely because another looks similar.

The fingerprint is an index/candidate aid, not a globally unique constraint: two legitimate activities can look identical.

### Update semantics

- Upsert imported provider-owned fields when source `updatedAt` or content hash changed.
- Preserve local feedback, local notes where separately owned, confirmed matches, and internal IDs.
- Treat provider disappearance as “missing remotely” first; soft-delete/archive only after reconciliation policy, never during a transient partial response.
- Track changed date ranges and recalculate only dependent summaries.

### Cursor transaction rule

Persist page mutations and its next cursor/watermark in one transaction. If the process fails before commit, replaying the page is safe. Advance the high-watermark only after all pages complete, while retaining the page cursor for resumability.

### Retry and rate limits

- Transient network, 408, 429, and 5xx: bounded exponential backoff with jitter; honor `Retry-After`.
- 401/403: no blind retries; mark connection action-required.
- malformed item: quarantine/log that item when safe and continue, or fail the page if cursor advancement would lose it.
- validation/database invariant: no transient retry loop; expose diagnostics.

Store opaque provider cursor state rather than assuming every provider can be represented by one timestamp. Include provider revision or payload checksum per source record so overlap fetches can no-op unchanged items.

### Sync status

Show connection status, last attempt/success, running/queued/failed state, imported/updated/skipped counts, next automatic run, and a sanitized error code/message. Keep detailed exception data in protected logs. Use a correlation ID linking UI run, Hangfire job, HTTP trace, and sync log.

### Publication idempotency

One publication row per local workout/connection, remote ID after create, canonical content hash, and optimistic version. A retry after an uncertain create should search/reconcile using a stable client correlation marker if the provider supports it before creating again. If it does not, serialize creation and mark uncertain outcomes for reconciliation rather than blindly retrying POST.

## 30. MVC page structure

Use conventional MVC areas/features and Razor partials. Bootstrap is recommended for the MVP because its accessible components, forms, and layout work directly with Razor without a separate CSS build pipeline. Tailwind is reasonable if the team already has design-system expertise.

| Navigation/page | Main behavior |
|---|---|
| `/` Dashboard | next workout, explanation, today, upcoming competition, trends, sync |
| `/Calendar` | week default; day/month; mixed event sources; drag/drop |
| `/Activities` | paged filters/list; details and feedback edit |
| `/Goals` | goals and competitions |
| `/Planner` | context summary, generate seven days, proposal review/approval |
| `/Workouts` | scheduled workouts and template library/builder |
| `/Schedule` | recurring training, exceptions, availability |
| `/Analytics` | volume/load/RPE/Feeling/planned-actual |
| `/Integrations` | connection, sync now, status/history/conflicts |
| `/Settings` | athlete, sports/zones/preferences/account |
| `/api/v1/external-activities` | machine-authenticated ingestion only |

HTMX is useful for:

- calendar range/filters and quick-edit modals;
- drag/drop POST with fragment refresh;
- sync enqueue/status fragment;
- proposal validation and approval fragments;
- workout-step editor operations.

Every HTMX route must also return coherent validation errors and enforce normal authorization/anti-forgery. Prefer progressive enhancement for forms. For drag/drop, provide keyboard/form alternatives. Use small JavaScript modules only where calendar interactions require them; HTMX is not a replacement for all client state.

## 31. Project and folder structure

```text
TrainingPlanner.sln
src/
  TrainingPlanner.Domain/
    Athletes/
    Activities/
    Planning/
    Scheduling/
    Goals/
    Workouts/
    Common/
  TrainingPlanner.Application/
    Abstractions/
      Persistence/
      Activities/
      Workouts/
      Ai/
      Time/
    Athletes/
    Activities/
      Import/
      Matching/
      Feedback/
      Queries/
    Calendar/
    Goals/
    Planning/
      Context/
      Proposals/
      Validation/
    Scheduling/
    Summaries/
    Workouts/
    DependencyInjection.cs
  TrainingPlanner.Infrastructure/
    Persistence/
      Configurations/
      Migrations/
      Repositories/
    Identity/
    Integrations/
      IntervalsIcu/
        Activities/
        Workouts/
        Auth/
      OpenAi/
      ExternalIngestion/
    BackgroundJobs/
    Observability/
    Security/
    DependencyInjection.cs
  TrainingPlanner.Web/
    Controllers/
    Models/                 # page/view/input models
    Views/
    Features/               # optional feature grouping, choose one convention
    Api/
    Authorization/
    wwwroot/
    Program.cs
tests/
  TrainingPlanner.Domain.Tests/
  TrainingPlanner.Application.Tests/
  TrainingPlanner.IntegrationTests/
```

The requested four production projects are sufficient. Use three test projects because their runtime needs differ; if repository simplicity is paramount, Application and Domain unit tests can begin in one unit-test project.

Dependency direction:

```text
Domain ← Application ← Web
Domain ← Application ← Infrastructure
Web composes Application + Infrastructure
```

Infrastructure implements Application ports. Web owns HTTP concerns and view models. Domain has no EF, MVC, provider, AI, Hangfire, or logging dependency.

Avoid a separate project for every feature, MediatR/CQRS solely for ceremony, generic repositories over EF Core, a service bus, event sourcing, and a generic plugin system. EF Core `DbContext` behind focused application abstractions is adequate.

The existing `FitChamp.csproj`, Python scripts, and workflow should be moved only in a deliberate later repository migration. During the first slice, introduce the solution beside them or place legacy tooling under `tools/` in a separate commit so history and current behavior remain clear.

## 32. Security

### Authentication and authorization

- ASP.NET Core Identity with secure cookies, confirmed account policy appropriate to deployment, lockout, and strong password defaults.
- Require authorization globally; explicitly allow login/register/health endpoints.
- Resource authorization checks `AthleteId` ownership on every command/query, not just hidden UI links.
- Anti-forgery on browser mutations including HTMX.
- Separate bearer API-key scheme for GitHub Action; never accept its credential as a browser session.
- Rate-limit login, AI generation, sync-now, and machine ingestion.
- HTTPS, secure/Httponly/SameSite cookies, HSTS in production, and restrictive headers/CSP.

### Secret storage

- **Local development:** .NET user-secrets or environment variables outside source control; a developer-specific Intervals connection can be encrypted with a local Data Protection key.
- **Docker development:** `.env` excluded from Git only for local convenience; prefer Docker secrets where supported. Never bake secrets into images or Compose files.
- **Production:** platform secret manager (Azure Key Vault, AWS Secrets Manager, GCP Secret Manager, Vault, or orchestrator secrets) mounted/injected at runtime. OpenAI application key should normally be configuration, not a per-user database row.
- **Per-user provider credentials:** encrypt at rest with ASP.NET Core Data Protection keys persisted outside the application container and protected by a production key-management service. Store ciphertext plus key/version metadata; support rotation.
- **Machine API keys:** store only a cryptographic hash/pepper-protected verifier, never reversible plaintext.

Database, Hangfire dashboard, health details, telemetry exporters, and admin endpoints must not be public by default. Protect Hangfire with explicit admin authorization or disable its dashboard.

Do not log authorization headers, cookies, prompts containing private notes, credential payloads, or raw provider responses by default.

## 33. Logging / observability

Use Serilog as the structured logging provider and OpenTelemetry for traces and metrics. Export through OTLP in production; console output is enough locally.

Standard dimensions:

```text
CorrelationId, TraceId, AthleteId (opaque/internal), ConnectionId,
Provider, SyncRunId, JobId, ProposalId, WorkoutId, Outcome
```

Instrument:

- HTTP/MVC, HttpClient, Npgsql/EF Core, and Hangfire traces;
- provider request duration/status/retry/rate-limit metrics;
- sync duration and imported/updated/duplicate/quarantined counts;
- AI duration, outcome, schema failures, model/schema/prompt version, and token usage where available;
- validation errors/warnings by code;
- publication create/update/no-op/conflict/failure;
- job queue, duration, retry, and failure;
- calendar/dashboard query duration.

Use correlation-ID middleware that accepts only safe bounded incoming IDs or creates one, returns it in the response, and enriches logs. Trace context should flow through Hangfire job arguments/state where possible.

Health checks:

- liveness: process only;
- readiness: PostgreSQL and required local dependencies;
- external providers are diagnostic/degraded checks, not readiness blockers, because local reads should remain available.

Set retention and sampling deliberately. High-cardinality external IDs and user free text do not belong in metric labels.

## 34. Testing strategy

### Domain tests

- workout-step tree invariants and derived duration;
- status transitions, lock behavior, goal/competition invariants;
- load evidence selection and missing-data semantics;
- recurrence occurrence/exception resolution across timezone/DST boundaries.

### Application tests

- context summarization and missingness;
- validator error/warning rules;
- proposal approval and stale-context handling;
- deterministic planned-actual scoring;
- import orchestration, cursor transaction behavior, and ownership authorization.
- transactional outbox dispatch replay without duplicate follow-up effects.

Use fakes for ports; do not mock every entity.

### Infrastructure/provider contract tests

- recorded/synthetic Intervals JSON maps to normalized values;
- unknown sport/Feeling and absent RPE remain safe/null;
- HttpClient behavior for pagination, 429 `Retry-After`, 401, timeout, and malformed item;
- workout serialization and unsupported capability errors;
- credential encryption round trip without exposing ciphertext/plaintext.

Keep provider fixtures sanitized and versioned. Do not depend on a live personal Intervals account in CI.

### PostgreSQL integration tests with Testcontainers

- actual migrations apply from empty database;
- indexes/unique constraints enforce source and publication idempotency;
- duplicate import replay produces one activity/source link;
- provider update changes provider-owned fields but not user feedback;
- cursor and page commit are atomic;
- cross-athlete queries/mutations are denied;
- Hangfire job persistence/locking where valuable.

### Required scenarios

1. Duplicate Intervals activity imported twice.
2. Existing Intervals activity updated.
3. Activity with missing RPE.
4. Wrestling activity with no RPE/Feeling gets optional assumed load, not fabricated feedback.
5. One clear planned-workout match and one ambiguous match.
6. Failed transient sync retries without duplicate writes.
7. Workout publish retry creates at most one remote workout.
8. AI response violates schema or target ranges.
9. Validator blocks overlap, unavailable time, fixed wrestling move, and A-race move.
10. Harder-than-planned activity appears in the next context.
11. Prompt injection text in an activity title/note is treated as data and cannot bypass proposal approval.
12. Recurrence around ambiguous and nonexistent daylight-saving times resolves according to the documented policy.

Use xUnit, WebApplicationFactory for HTTP/UI integration boundaries, and a fake HTTP handler or local stub server for provider behavior. Add a small number of browser tests only after critical HTMX/drag-drop flows exist; they are not a substitute for application tests.

## 35. Docker development environment

Recommended containers:

```text
web         ASP.NET Core application; also runs Hangfire Server for MVP
postgres    PostgreSQL with named volume and health check
otel        optional OpenTelemetry Collector profile
```

One web process hosting Hangfire is pragmatic for single-user MVP. Ensure jobs use distributed locks and graceful shutdown. Split a worker container from the same image later if provider/AI jobs interfere with web latency.

Development workflow:

- multi-stage .NET 10 Dockerfile;
- non-root runtime user;
- pinned major PostgreSQL image and locked NuGet versions;
- Compose health-based dependency, named volume, and local ports bound conservatively;
- migration command/one-shot service or application startup migration guarded by a deployment lock for development.

For production, run migrations as an explicit deployment step, not concurrently from every replica. Persist Data Protection keys externally. Do not include Intervals/OpenAI secrets in the image. Back up PostgreSQL and test restore procedures.

Testcontainers should launch its own PostgreSQL container and not rely on the developer Compose database.

## 36. Ordered implementation roadmap

Each step should leave a demonstrable vertical capability, not only layers of abstractions.

1. **Foundation and first vertical slice:** solution/projects, MVC, PostgreSQL, migrations, Identity, athlete timezone, Intervals connection, initial import, local activity list, basic weekly calendar.
2. **Reliable synchronization:** incremental cursor/overlap, sync runs/status, Hangfire schedule/manual enqueue, retries/rate limits, idempotency and mapping/integration tests.
3. **Schedule constraints:** recurring wrestling rules/exceptions, availability rules/exceptions, goals, competitions, and calendar composition.
4. **Planned workouts:** planned-workout aggregate, structured step tree, templates, quick edit/drag-drop, locks/status.
5. **Publication:** Intervals workout translation, publication identity/hash, updates, conflict and cancel behavior.
6. **Completion and adaptation data:** deterministic matching, user confirmation, planned-versus-actual metrics, load selection, daily/weekly summaries.
7. **AI seven-day planning:** TrainingContext, strict schema, proposal persistence, deterministic validator, review/edit/approve, publication enqueue.
8. **Dashboard and weekly review:** next-workout explanation, trends, factual weekly summary, optional AI narrative.
9. **Coach chat and focused replans:** bounded context, proposal-producing commands, regenerate/ease/shorten/move.
10. **Operational hardening:** telemetry dashboards/alerts, secret rotation, backups, accessibility/performance checks, retention/privacy operations.
11. **Post-MVP adapters:** GitHub Action ingestion first if useful, then Zwift/Garmin only after API feasibility and user value are confirmed.

Do not begin by implementing every entity. Build only what the current slice needs, while preserving the boundaries and keys in this plan.

## 37. Architectural risks

| Risk | Consequence | Mitigation |
|---|---|---|
| Intervals API semantics/limits differ from assumptions | broken incremental sync or duplicate exports | API spike against official docs; contract fixtures; cursor overlap; publication reconciliation |
| Cross-provider duplicate ambiguity | double-counted training stress or bad merge | exact source uniqueness, conservative scoring, user-confirmed merge, reversible source links |
| Mixed-sport load is not comparable | misleading planning | preserve method/provenance, show duration and sport splits, version policy, avoid false precision |
| AI hallucinates or ignores constraints | unsafe/infeasible plan | strict schema, bounded context, deterministic validator, approval, no direct tools |
| Context becomes too large/stale | cost, latency, poor plan | windowed summaries, hashes/versions, proposal expiry, pre-approval revalidation |
| Recurrence and DST errors | shifted/missed fixed training | IANA timezone, local recurrence semantics, explicit occurrence dates, DST tests |
| Concurrent sync/manual requests | duplicates/cursor corruption | per-stream distributed lock, transactions, unique constraints, idempotent upserts |
| Uncertain remote POST result | duplicate external workouts | client marker where possible, serialized create, reconciliation before retry |
| Secret encryption keys lost | integrations unrecoverable | external persistent Data Protection key ring, KMS protection, backup/rotation procedure |
| Single web+worker resource contention | slow pages | job queues/concurrency limits; split worker from same image when measured |
| Calendar UI complexity/accessibility | fragile key workflow | server-owned model, progressive enhancement, keyboard list/form alternative |
| Existing Garmin tooling confuses product boundary | accidental MVP scope expansion | keep legacy tool isolated; treat future endpoint/provider work as separate adapters |
| “Single user” shortcuts leak into code | expensive future ownership retrofit | Identity + AthleteId and resource authorization from first migration |

## 38. Decisions still required before coding

Resolve or time-box these decisions during the relevant slice:

1. **Intervals.icu API details:** authentication option, athlete identifier, activity updated-since/paging support, exact RPE/Feeling scales, workout create/update/delete format, client correlation fields, conflict/version metadata, and rate limits.
2. **Initial import range:** default 90 or 180 days. Recommendation: 90 for speed, with user-selectable 180 before first import.
3. **Timezone behavior:** confirm the athlete’s IANA timezone and policy when it changes. Recommendation: preserve each activity’s imported local date/timezone and apply the new timezone only to future schedule rules.
4. **Week definition:** Monday/ISO week versus locale-configurable. Recommendation: Monday/ISO for MVP.
5. **Training load precedence/scales:** whether Intervals load is trusted above local calculations and how wrestling default 75 relates to cycling load.
6. **Thresholds:** hard-session definition, max weekly increase warning percentage, matching windows/confidence, and partial-completion thresholds. Make these configuration/policy values, not unexplained constants.
7. **Availability representation:** daily max only versus multiple time windows. Recommendation: max plus optional single window in MVP unless split-day scheduling is immediately needed.
8. **Calendar UI component:** custom/lightweight component versus a third-party calendar library. Evaluate licensing, accessibility, Razor/HTMX integration, and drag/drop.
9. **CSS:** Bootstrap or Tailwind. Recommendation: Bootstrap for the first slice.
10. **Identity registration:** open registration, invite/admin-created first user, or deployment-seeded user. Recommendation for a personal deployment: disable open registration after creating the owner.
11. **Secret platform:** deployment target determines KMS/secret manager and Data Protection key persistence.
12. **AI model/data policy:** selected OpenAI model, retention settings, budget/token limits, free-text inclusion, and whether raw redacted snapshots expire.
13. **Proposal granularity:** approval of whole proposal versus selected operations. Recommendation: whole proposal in MVP; selected operations later if review UX demands it.
14. **Legacy tooling location:** retain at repository root temporarily or move to `tools/wrestling-fit-generator`. Make this a separate, behavior-preserving change.
15. **GitHub ingestion timing:** it is optional and should not delay the Intervals-first slice.

## Recommended first vertical slice

Build the smallest end-to-end proof that establishes the architectural spine:

### User-visible outcome

A user can log in, enter their athlete timezone, connect Intervals.icu, request an initial import, and see locally stored activities in a paged list and basic Monday-to-Sunday calendar. Disconnecting Intervals or simulating an outage does not remove the displayed data.

### Included implementation

1. Create `TrainingPlanner.sln` and the four production projects plus unit/integration test projects.
2. Add Docker Compose PostgreSQL, EF Core context/migrations, Identity, and one `AthleteProfile`.
3. Implement only the activity fields needed to display the initial list/calendar, but include nullable normalized metrics, `AthleteId`, feedback nullability, and source-link uniqueness.
4. Implement `IActivitySource`, `IntervalsIcuActivitySource`, provider DTO mapping, and one application import orchestrator.
5. Store an encrypted Intervals connection, `SyncState`, and `SyncRun`.
6. Enqueue initial import through Hangfire; expose “Sync now” and status.
7. Render `/Activities` and `/Calendar?view=week&date=...` from PostgreSQL using Razor; use HTMX only for week navigation/status refresh if helpful.
8. Add structured logs/traces around import and database operations.
9. Prove with xUnit/Testcontainers:
   - migrations apply;
   - duplicate replay remains one activity;
   - changed source activity updates;
   - missing RPE/Feeling remains null;
   - provider failure leaves local pages available.

### Explicitly deferred from the first slice

AI, planned workouts, publication, recurrence, matching, analytics, zones, drag/drop, GitHub ingestion, and Garmin/Zwift. Those are not needed to validate the highest-risk foundation: provider isolation, idempotent local persistence, athlete ownership, and calendar reads.

### Acceptance criteria

- A clean checkout starts web + PostgreSQL using documented Docker commands.
- An authenticated owner can connect using secrets that never appear in logs or database plaintext.
- Importing the same provider response twice creates one source link and one activity.
- An updated provider response updates provider-owned local fields.
- Activities page and week calendar execute no Intervals.icu request.
- A simulated 429/5xx is visible as a sanitized failed sync and does not affect existing activity reads.
- Integration tests use a real ephemeral PostgreSQL database and a fake/stub provider, not a live account.

This slice is intentionally not a skeleton of every future feature. It produces a deployable, testable capability and establishes the boundaries all later planning features depend on.
