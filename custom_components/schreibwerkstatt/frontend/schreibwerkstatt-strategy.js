// Dashboard strategy for the Schreibwerkstatt integration.
//
//   strategy:
//     type: custom:schreibwerkstatt
//     entry_id: …        # optional, only with several Schreibwerkstatt servers
//
// Built-in cards only. Entity IDs come from the integration (websocket
// `schreibwerkstatt/entities`), never from names: they depend on the users'
// display names and the HA language. One section per user, a daily-goal gauge
// only where a goal is set, one series per AI model — all as reported now.
// "Take control" in the dashboard menu turns the result into editable YAML.

const TEXT = {
  de: {
    title: "Schreibwerkstatt",
    today: "Heute", history: "Verlauf", ops: "Bestand & Betrieb", diag: "Diagnose",
    writtenToday: "Heute geschrieben", writingHeading: "Schreiben", writing: "Schreibzeit", words: "Wörter", wordsToday: "Wörter heute",
    editing: "Lektorat", dictation: "Diktat", dictatedChars: "Diktierte Zeichen",
    writing7: "Schreibzeit – 7 Tage", goal: "Tagesziel", aiToday: "KI heute", aiMonth: "KI Monat",
    aiTotal: "KI gesamt", books: "Bücher", aiCost: "KI-Kosten", thisMonth: "Dieser Monat",
    billed: "Anthropic abgerechnet", costPerDay: "Kosten pro Tag – 30 Tage",
    times: "Schreib-, Lektorats- und Diktatzeit pro Tag", netWords: "Netto-Wörter pro Tag",
    wordsStock: "Wörter im Bestand", perPerson: "Pro Person", writingPerPerson: "Schreibzeit pro Person",
    goalPerPerson: "Tagesziel pro Person (%)", aiPerPerson: "KI-Kosten pro Person",
    goalReached7: "Tagesziel erreicht – 7 Tage", ai: "KI", costPerMonth: "KI-Kosten pro Monat",
    ledger: "Ledger", inputPerDay: "Input-Tokens pro Tag", outputPerDay: "Output-Tokens pro Tag (inkl. Denken)",
    cacheRead: "Cache", cacheReadTokens: "Cache-Read-Tokens", cacheWriteTokens: "Cache-Write-Tokens",
    otherPeople: "Weitere Personen – länger nicht gesehen",
    stock: "Bestand", chapters: "Kapitel", pages: "Seiten", normPages: "Normseiten", chars: "Zeichen",
    users: "Benutzer", active24: "Aktiv 24 h", active7: "Aktiv 7 Tage",
    status: { active: "Aktiv", invited: "Eingeladen", suspended: "Gesperrt", deleted: "Gelöscht" },
    registrations: "Offene Registrierungen", registrationsShort: "Registrierungen",
    jobs: "Jobs", running: "Laufend", queued: "Wartend", ended24: "Beendet in 24 h",
    jobStatus: { done: "Erfolgreich", error: "Fehler", cancelled: "Abgebrochen" },
    jobs24: "Jobs – 24 h", failedJobs: "Fehlgeschlagene Jobs", jobsRunning: "Jobs laufen",
    server: "Server", database: "Datenbank", dbSize: "Datenbankgrösse", jsErrors: "JS-Fehler 24 h",
    aiTotals: "KI-Gesamtkosten", inputTokens: "Input-Tokens", outputTokens: "Output-Tokens",
    process: "Prozess", uptime: "Laufzeit", schema: "Schema", memory24: "Speicher – 24 h",
    memory: "Arbeitsspeicher", heap: "Heap", merge: "Block-Merge", silent: "Still",
    conflicts: "Konflikte", overwritten: "Überschrieben", resolved: "Konflikte gelöst",
    choice: { local: "Lokal", remote: "Server", both: "Beide" },
    billing: "Abrechnung", billedDiff: "Abweichung Anthropic ↔ Ledger", more: "Weitere Werte",
    moreHint:
      "Aufschlüsselungen mit vielen Label-Kombinationen (Kosten nach Job-Typ, Cache-Tokens, " +
      "Job-Historie je Typ …) sind standardmässig deaktiviert. Unter *Einstellungen → Geräte & " +
      "Dienste → Schreibwerkstatt → Entitäten* aktivieren – sie erscheinen dann hier.",
    noUsers:
      "Keine Werte pro Person: Das API-Token liefert keine **Per-user values**. In Schreibwerkstatt " +
      "unter *Admin → Einstellungen → API / Metrics* ein Token mit dieser Option erstellen und " +
      "in Home Assistant neu authentifizieren.",
    noGoal: "Kein Tagesziel gesetzt.",
    notLoaded: "Die Integration Schreibwerkstatt ist nicht eingerichtet oder nicht geladen.",
  },
  en: {
    title: "Schreibwerkstatt",
    today: "Today", history: "History", ops: "Content & operations", diag: "Diagnostics",
    writtenToday: "Written today", writingHeading: "Writing", writing: "Writing time", words: "Words", wordsToday: "Words today",
    editing: "Editing", dictation: "Dictation", dictatedChars: "Dictated characters",
    writing7: "Writing time – 7 days", goal: "Daily goal", aiToday: "AI today", aiMonth: "AI month",
    aiTotal: "AI total", books: "Books", aiCost: "AI cost", thisMonth: "This month",
    billed: "Billed by Anthropic", costPerDay: "Cost per day – 30 days",
    times: "Writing, editing and dictation time per day", netWords: "Net words per day",
    wordsStock: "Words in stock", perPerson: "Per person", writingPerPerson: "Writing time per person",
    goalPerPerson: "Daily goal per person (%)", aiPerPerson: "AI cost per person",
    goalReached7: "Daily goal reached – 7 days", ai: "AI", costPerMonth: "AI cost per month",
    ledger: "Ledger", inputPerDay: "Input tokens per day", outputPerDay: "Output tokens per day (incl. thinking)",
    cacheRead: "Cache", cacheReadTokens: "Cache read tokens", cacheWriteTokens: "Cache write tokens",
    otherPeople: "Other people – not seen recently",
    stock: "Content", chapters: "Chapters", pages: "Pages", normPages: "Standard pages", chars: "Characters",
    users: "Users", active24: "Active 24 h", active7: "Active 7 days",
    status: { active: "Active", invited: "Invited", suspended: "Suspended", deleted: "Deleted" },
    registrations: "Pending registrations", registrationsShort: "Registrations",
    jobs: "Jobs", running: "Running", queued: "Queued", ended24: "Finished in 24 h",
    jobStatus: { done: "Done", error: "Failed", cancelled: "Cancelled" },
    jobs24: "Jobs – 24 h", failedJobs: "Failed jobs", jobsRunning: "Jobs running",
    server: "Server", database: "Database", dbSize: "Database size", jsErrors: "JS errors 24 h",
    aiTotals: "AI cost total", inputTokens: "Input tokens", outputTokens: "Output tokens",
    process: "Process", uptime: "Uptime", schema: "Schema", memory24: "Memory – 24 h",
    memory: "Memory", heap: "Heap", merge: "Block merge", silent: "Silent",
    conflicts: "Conflicts", overwritten: "Overwritten", resolved: "Conflicts resolved",
    choice: { local: "Local", remote: "Server", both: "Both" },
    billing: "Billing", billedDiff: "Difference Anthropic ↔ ledger", more: "More values",
    moreHint:
      "Breakdowns with many label combinations (cost per job type, cache tokens, job history " +
      "per type …) are disabled by default. Enable them under *Settings → Devices & services → " +
      "Schreibwerkstatt → Entities* and they show up here.",
    noUsers:
      "No per-user values: the API token does not include **Per-user values**. Create a token " +
      "with this option in Schreibwerkstatt (*Admin → Settings → API / Metrics*) and " +
      "re-authenticate in Home Assistant.",
    noGoal: "No daily goal set.",
    notLoaded: "The Schreibwerkstatt integration is not set up or not loaded.",
  },
};

const compact = (list) => list.flat().filter(Boolean);

// Lookup of entity IDs by metric, labels and user.
class Entities {
  constructor(entities) {
    this.all = entities;
    this.used = new Set();
  }

  list(metric, user = null) {
    return this.all.filter((e) => e.metric === metric && e.user === user);
  }

  id(metric, labels = {}, user = null) {
    const hit = this.list(metric, user).find((e) =>
      Object.entries(labels).every(([k, v]) => e.labels[k] === v),
    );
    if (!hit) return undefined;
    this.used.add(hit.entity_id);
    return hit.entity_id;
  }

  // A user shown only in the compact list: their other values must not end up under
  // "More values" either.
  retire(user) {
    for (const e of this.all) if (e.user === user) this.used.add(e.entity_id);
  }

  unused() {
    return this.all.filter((e) => !this.used.has(e.entity_id)).map((e) => e.entity_id);
  }
}

const tile = (entity, name, color, extra = {}) => entity && { type: "tile", entity, name, color, ...extra };

const rows = (pairs) => pairs.filter(([entity]) => entity).map(([entity, name]) => ({ entity, name }));

function glance(pairs, extra = {}) {
  const entities = rows(pairs);
  return entities.length > 0 && { type: "glance", entities, ...extra };
}

function stats(title, pairs, stat, opts = {}) {
  const entities = rows(pairs);
  if (entities.length === 0) return null;
  return {
    type: "statistics-graph",
    title,
    entities,
    chart_type: "bar",
    period: "day",
    days_to_show: 30,
    stat_types: [stat],
    ...(entities.length === 1 ? { hide_legend: true } : {}),
    ...opts,
  };
}

function history(title, hours, pairs) {
  const entities = rows(pairs);
  return entities.length > 0 && { type: "history-graph", title, hours_to_show: hours, entities };
}

// A section only when it has something besides its heading.
function section(heading, icon, cards, { badges, ...extra } = {}) {
  const body = compact(cards);
  if (body.length === 0) return null;
  const head = { type: "heading", heading, icon, ...(badges ? { badges: compact(badges) } : {}) };
  return { type: "grid", ...extra, cards: [head, ...body] };
}

function view(title, path, icon, sections, extra = {}) {
  return { title, path, icon, type: "sections", ...extra, sections: compact(sections) };
}

// Badge that only shows while the value is above zero.
function alertBadge(entity, name, color, extra = {}) {
  return (
    entity && {
      type: "entity",
      entity,
      name,
      show_name: true,
      color,
      visibility: [{ condition: "numeric_state", entity, above: 0 }],
      ...extra,
    }
  );
}

// Label of an AI sample: the model, Claude IDs shortened (claude-opus-5-5 → Opus 5.5,
// claude-opus-4-8[1m] → Opus 4.8 (1M)); anything else as reported.
function modelName(labels) {
  const model = labels.model || labels.provider || "";
  const m = /^claude-([a-z]+)-(\d+)(?:-(\d{1,2}))?(?:-\d{8})?(\[1m\])?$/.exec(model);
  if (!m) return model;
  const family = m[1][0].toUpperCase() + m[1].slice(1);
  return `${family} ${m[2]}${m[3] ? `.${m[3]}` : ""}${m[4] ? " (1M)" : ""}`;
}

const modelKey = (labels) => `${labels.provider}|${labels.model}`;

// Input tokens per model over the last 30 days, from the recorder's long-term statistics.
// The ledger counts every model ever used, so all-time totals would put a model retired
// long ago ahead of the one in use now. No recorder or no statistics yet: usage unknown.
async function modelUsage(hass, ent) {
  const usage = new Map();
  await Promise.all(
    ent.list("sw_tokens_in_total").map(async (e) => {
      try {
        const res = await hass.callWS({
          type: "recorder/statistic_during_period",
          statistic_id: e.entity_id,
          rolling_window: { duration: { days: 30 } },
          types: ["change"],
        });
        if (typeof res?.change === "number") usage.set(modelKey(e.labels), res.change);
      } catch {
        // Usage stays unknown; the model is shown.
      }
    }),
  );
  return usage;
}

// Most used in the last 30 days first; unknown usage after, in reported order.
const byUsage = (models, usage) =>
  [...models].sort((a, b) => (usage.get(modelKey(b)) ?? -1) - (usage.get(modelKey(a)) ?? -1));

// Models for the daily charts: only those in use. Unknown usage counts as in use.
const inUse = (models, usage) => byUsage(models, usage).filter((l) => usage.get(modelKey(l)) !== 0);

const ACTIVE_DAYS = 14;

// Seen within ACTIVE_DAYS. Without a last-seen value (sensor off, not yet reported): active.
function isActive(hass, ent, user) {
  const seen = ent.list("sw_user_last_seen_timestamp_seconds", user.user)[0];
  const t = Date.parse(seen && hass.states[seen.entity_id]?.state);
  return Number.isNaN(t) || Date.now() - t < ACTIVE_DAYS * 86400_000;
}

// Exactly zero, not unknown or unavailable.
const isZero = (hass, entity) => entity !== undefined && Number(hass.states[entity]?.state ?? NaN) === 0;

function userSection(t, ent, hass, user) {
  const u = user.user;
  const goal = ent.id("sw_user_daily_goal_percent", {}, u);
  const reached = ent.id("daily_goal_reached", {}, u);
  const seen = ent.id("sw_user_last_seen_timestamp_seconds", {}, u);
  const aiToday = ent.id("sw_user_cost_usd_today", {}, u);
  const aiMonth = ent.id("sw_user_cost_usd_month", {}, u);
  const aiTotal = ent.id("sw_user_cost_usd_total", {}, u);
  // Never used AI: two tiles at 0 $ say nothing. They appear once there is a cost.
  const usesAi = !isZero(hass, aiTotal);
  return section(
    user.name,
    "mdi:account-edit",
    [
      goal
        ? {
            type: "gauge",
            entity: goal,
            name: t.goal,
            min: 0,
            max: 100,
            needle: true,
            segments: [
              { from: 0, color: "#e0e0e0" },
              { from: 50, color: "#ffb74d" },
              { from: 100, color: "#66bb6a" },
            ],
          }
        : null,
      tile(ent.id("sw_user_writing_seconds_today", {}, u), t.writing, "indigo"),
      tile(ent.id("sw_user_words_today", {}, u), t.wordsToday, "indigo"),
      tile(ent.id("sw_user_lektorat_seconds_today", {}, u), t.editing, "purple"),
      tile(ent.id("sw_user_stt_seconds_today", {}, u), t.dictation, "teal"),
      usesAi && tile(aiToday, t.aiToday, "amber"),
      usesAi && tile(aiMonth, t.aiMonth, "amber"),
      glance(
        [
          [ent.id("sw_user_books", {}, u), t.books],
          [ent.id("sw_user_words", {}, u), t.words],
          [usesAi && aiTotal, t.aiTotal],
        ],
        { show_icon: false, state_color: false },
      ),
    ],
    {
      badges: [
        seen && { type: "entity", entity: seen, icon: "mdi:account-clock" },
        reached && {
          type: "entity",
          entity: reached,
          show_state: false,
          icon: "mdi:trophy",
          color: "amber",
          visibility: [{ condition: "state", entity: reached, state: "on" }],
        },
      ],
    },
  );
}

// People not seen for ACTIVE_DAYS: one row each with when they were last seen.
function dormantSection(t, ent, users) {
  const entities = users.map((user) => {
    const seen = ent.id("sw_user_last_seen_timestamp_seconds", {}, user.user);
    ent.retire(user.user);
    return seen && { entity: seen, name: user.name, icon: "mdi:account-clock" };
  });
  return section(t.otherPeople, "mdi:account-multiple-outline", [
    compact(entities).length > 0 && { type: "entities", entities: compact(entities), state_color: false },
  ]);
}

function todayView(t, ent, entry, hass, people) {
  const failed = ent.id("sw_jobs_ended_24h", { status: "error" });
  const running = ent.id("sw_jobs_running");
  const pending = ent.id("sw_registration_requests_pending");
  const writing = ent.id("sw_writing_seconds_today");
  const costToday = ent.id("sw_cost_usd_today");
  const billed = ent.id("sw_billed_usd_month");
  // Token without per-user values: say so instead of silently showing nobody.
  const noUsers =
    !entry.includes_users && section(t.perPerson, "mdi:account-group", [{ type: "markdown", content: t.noUsers }]);

  return view(
    t.today,
    "heute",
    "mdi:fountain-pen-tip",
    [
      section(
        t.writtenToday,
        "mdi:calendar-today",
        [
          tile(writing, t.writing, "indigo", { grid_options: { columns: 12 } }),
          tile(ent.id("sw_words_today"), t.words, "indigo"),
          tile(ent.id("sw_lektorat_seconds_today"), t.editing, "purple"),
          tile(ent.id("sw_stt_seconds_today"), t.dictation, "teal"),
          tile(ent.id("sw_stt_chars_today"), t.dictatedChars, "teal"),
          stats(t.writing7, [[writing, t.writing]], "change", { days_to_show: 7 }),
        ],
        {
          badges: [
            ent.id("sw_active_users_24h") && {
              type: "entity",
              entity: ent.id("sw_active_users_24h"),
              icon: "mdi:account-clock",
              color: "green",
            },
          ],
        },
      ),
      ...people.active.map((user) => userSection(t, ent, hass, user)),
      noUsers,
      section(t.aiCost, "mdi:robot-outline", [
        tile(costToday, t.today, "amber"),
        tile(ent.id("sw_cost_usd_month"), t.thisMonth, "amber"),
        tile(billed, t.billed, "deep-orange", { icon: "mdi:receipt-text", grid_options: { columns: 12 } }),
        stats(t.costPerDay, [[costToday, t.aiCost]], "change"),
      ]),
      dormantSection(t, ent, people.dormant),
    ],
    {
      max_columns: 4,
      badges: compact([
        alertBadge(pending, t.registrationsShort, "orange", {
          tap_action: { action: "navigate", navigation_path: "/config/integrations/integration/schreibwerkstatt" },
        }),
        alertBadge(failed, t.failedJobs, "red"),
        alertBadge(running, t.jobsRunning, "blue"),
      ]),
    },
  );
}

function historyView(t, ent, hass, people, usage) {
  const id = (m, l) => ent.id(m, l);
  const per = (metric, users = people.active) => users.map((user) => [ent.id(metric, {}, user.user), user.name]);
  const aiUsers = people.active.filter((user) => !isZero(hass, ent.id("sw_user_cost_usd_total", {}, user.user)));
  const models = inUse(
    ent.list("sw_tokens_in_total").map((e) => e.labels),
    usage,
  );
  // One series per model in use.
  const series = (metric, prefix = "") =>
    models.map((labels) => [id(metric, labels), `${prefix}${modelName(labels)}`]);

  return view(
    t.history,
    "verlauf",
    "mdi:chart-bar",
    [
      section(
        t.writingHeading,
        "mdi:fountain-pen-tip",
        [
          stats(
            t.times,
            [
              [id("sw_writing_seconds_today"), t.writing],
              [id("sw_lektorat_seconds_today"), t.editing],
              [id("sw_stt_seconds_today"), t.dictation],
            ],
            "change",
            { grid_options: { columns: 12 } },
          ),
          stats(t.netWords, [[id("sw_words_today"), t.words]], "max"),
          stats(t.wordsStock, [[id("sw_words"), t.words]], "max", {
            chart_type: "line",
            period: "week",
            days_to_show: 365,
          }),
        ],
        { column_span: 2 },
      ),
      section(
        t.perPerson,
        "mdi:account-group",
        [
          stats(t.writingPerPerson, per("sw_user_writing_seconds_today"), "change"),
          stats(t.goalPerPerson, per("sw_user_daily_goal_percent"), "max"),
          stats(t.aiPerPerson, per("sw_user_cost_usd_today", aiUsers), "change"),
          history(t.goalReached7, 168, per("daily_goal_reached")),
        ],
        { column_span: 2 },
      ),
      section(
        t.ai,
        "mdi:robot-outline",
        [
          stats(
            t.costPerMonth,
            [
              [id("sw_cost_usd_month"), t.ledger],
              [id("sw_billed_usd_month"), "Anthropic"],
            ],
            "change",
            { period: "month", days_to_show: 365 },
          ),
          // Input and output apart: on models that think, output (thinking included) is
          // the expensive part and would vanish next to the input on a shared axis.
          stats(
            t.inputPerDay,
            [...series("sw_tokens_in_total"), ...series("sw_cache_read_tokens_total", `${t.cacheRead} · `)],
            "change",
          ),
          stats(t.outputPerDay, series("sw_tokens_out_total"), "change"),
        ],
        { column_span: 2 },
      ),
    ],
    { max_columns: 2 },
  );
}

function opsView(t, ent, usage) {
  const id = (m, l) => ent.id(m, l);
  const models = ent.list("sw_cost_usd_total").map((e) => e.labels);
  const tokenModels = ent.list("sw_tokens_in_total").map((e) => e.labels);
  // Every model ever used, the one in use first.
  const allModels = byUsage(
    [...new Map([...models, ...tokenModels].map((l) => [modelKey(l), l])).values()],
    usage,
  );

  return view(
    t.ops,
    "betrieb",
    "mdi:server",
    [
      section(t.stock, "mdi:bookshelf", [
        tile(id("sw_books"), t.books, "brown"),
        tile(id("sw_chapters"), t.chapters, "brown"),
        tile(id("sw_pages"), t.pages, "brown"),
        tile(id("sw_normseiten"), t.normPages, "brown"),
        tile(id("sw_words"), t.words, "indigo"),
        tile(id("sw_chars"), t.chars, "indigo"),
      ]),
      section(t.users, "mdi:account-multiple", [
        tile(id("sw_active_users_24h"), t.active24, "green"),
        tile(id("sw_active_users_7d"), t.active7, "green"),
        glance(
          ent.list("sw_users").map((e) => [id("sw_users", e.labels), t.status[e.labels.status] || e.labels.status]),
          { show_icon: false },
        ),
        tile(id("sw_registration_requests_pending"), t.registrations, "orange", { grid_options: { columns: 12 } }),
      ]),
      section(t.jobs, "mdi:cog-play", [
        tile(id("sw_jobs_running"), t.running, "blue"),
        tile(id("sw_jobs_queued"), t.queued, "blue"),
        glance(
          ent
            .list("sw_jobs_ended_24h")
            .map((e) => [id("sw_jobs_ended_24h", e.labels), t.jobStatus[e.labels.status] || e.labels.status]),
          { title: t.ended24 },
        ),
        history(t.jobs24, 24, [
          [id("sw_jobs_running"), t.running],
          [id("sw_jobs_queued"), t.queued],
        ]),
      ]),
      section(t.server, "mdi:server", [
        tile(id("sw_db_size_bytes"), t.database, "blue-grey"),
        tile(id("sw_js_errors_24h"), t.jsErrors, "red"),
        stats(t.dbSize, [[id("sw_db_size_bytes"), t.database]], "max", {
          chart_type: "line",
          days_to_show: 90,
        }),
      ]),
      section(
        t.aiTotals,
        "mdi:cash",
        allModels.map((labels) => {
          // Cache rows only once their (by default disabled) entities are enabled.
          const entities = rows([
            [id("sw_cost_usd_total", labels), t.aiTotal],
            [id("sw_tokens_in_total", labels), t.inputTokens],
            [id("sw_tokens_out_total", labels), t.outputTokens],
            [id("sw_cache_read_tokens_total", labels), t.cacheReadTokens],
            [id("sw_cache_creation_tokens_total", labels), t.cacheWriteTokens],
          ]);
          return entities.length > 0 && { type: "entities", title: modelName(labels), state_color: false, entities };
        }),
      ),
    ],
    { max_columns: 4 },
  );
}

function diagView(t, ent) {
  const id = (m, l) => ent.id(m, l);
  const sections = [
    section(t.process, "mdi:memory", [
      tile(id("sw_process_uptime_seconds"), t.uptime, "blue-grey"),
      tile(id("sw_db_schema_version"), t.schema, "blue-grey"),
      history(t.memory24, 24, [
        [id("sw_process_resident_memory_bytes"), t.memory],
        [id("sw_process_heap_used_bytes"), t.heap],
      ]),
    ]),
    section(t.merge, "mdi:source-merge", [
      glance(
        [
          [id("sw_merge_silent_total"), t.silent],
          [id("sw_merge_conflict_shown_total"), t.conflicts],
          [id("sw_merge_fallback_overwrite_total"), t.overwritten],
        ],
        { columns: 3 },
      ),
      glance(
        ent
          .list("sw_merge_conflict_resolved_total")
          .map((e) => [id("sw_merge_conflict_resolved_total", e.labels), t.choice[e.labels.choice] || e.labels.choice]),
        { title: t.resolved, columns: 3 },
      ),
    ]),
    section(t.billing, "mdi:receipt-text", [
      tile(id("sw_billed_diff_usd_month"), t.billedDiff, "deep-orange", {
        icon: "mdi:scale-unbalanced",
        grid_options: { columns: 12 },
      }),
    ]),
  ];
  // Everything not placed above: enabled breakdowns and metrics newer than this strategy.
  const rest = ent.unused();
  sections.push(
    section(t.more, "mdi:dots-horizontal", [
      rest.length > 0 && { type: "entities", entities: rest },
      { type: "markdown", content: t.moreHint },
    ]),
  );
  return view(t.diag, "diagnose", "mdi:stethoscope", sections, { max_columns: 3 });
}

function errorDashboard(t, message) {
  return {
    title: t.title,
    views: [{ title: t.title, type: "panel", cards: [{ type: "markdown", content: message }] }],
  };
}

class SchreibwerkstattDashboardStrategy extends HTMLElement {
  static async generate(config, hass) {
    const t = (hass.locale?.language || hass.language || "en").startsWith("de") ? TEXT.de : TEXT.en;
    let entries;
    try {
      ({ entries } = await hass.callWS({ type: "schreibwerkstatt/entities" }));
    } catch (err) {
      return errorDashboard(t, `${t.notLoaded}\n\n\`${err?.message || err?.code || err}\``);
    }
    const entry = config.entry_id ? entries.find((e) => e.entry_id === config.entry_id) : entries[0];
    if (!entry) return errorDashboard(t, t.notLoaded);

    const ent = new Entities(entry.entities);
    const usage = await modelUsage(hass, ent);
    const people = { active: [], dormant: [] };
    for (const user of entry.users) people[isActive(hass, ent, user) ? "active" : "dormant"].push(user);
    // Order matters: the diagnostics view collects what the others did not use.
    const views = [
      todayView(t, ent, entry, hass, people),
      historyView(t, ent, hass, people, usage),
      opsView(t, ent, usage),
      diagView(t, ent),
    ];
    return { title: config.title || (entries.length > 1 ? `${t.title} · ${entry.title}` : t.title), views };
  }
}

customElements.define("ll-strategy-dashboard-schreibwerkstatt", SchreibwerkstattDashboardStrategy);
