# Schreibwerkstatt for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/schreibwerkstatt/homeassistant/actions/workflows/validate.yml/badge.svg)](https://github.com/schreibwerkstatt/homeassistant/actions/workflows/validate.yml)
[![Tests](https://github.com/schreibwerkstatt/homeassistant/actions/workflows/tests.yml/badge.svg)](https://github.com/schreibwerkstatt/homeassistant/actions/workflows/tests.yml)

Brings a [Schreibwerkstatt](https://github.com/schreibwerkstatt/schreibwerkstatt) server into Home Assistant:
server health, users, content, writing activity, AI token usage and cost — and, if you allow it,
the same per user.

The integration reads the server's self-describing `/metrics.json`. Every metric carries its own
unit, device class, state class and display name, so new metrics, users and AI models appear in
Home Assistant automatically, without a new release of this integration.

## Requirements

- Schreibwerkstatt **4.16** or later (provides `/metrics.json`); **4.21** or later for characters
  per person and per day and for the [history back-fill](#history)
- Home Assistant **2025.1** or later
- An API token from Schreibwerkstatt: **Admin → Settings → API / Metrics → Create token**.
  Tick **Per-user values** to also receive writing time, characters, words, daily goal and cost per user
  (no book titles, no content). Issuing such a token is recorded in the admin audit log.

## Installation

### HACS

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/schreibwerkstatt/homeassistant`, category **Integration**.
2. Install **Schreibwerkstatt**, restart Home Assistant.
3. **Settings → Devices & services → Add integration → Schreibwerkstatt**.

### Manual

Copy `custom_components/schreibwerkstatt` into your Home Assistant `config/custom_components/` and restart.

## Configuration

| Field | |
|---|---|
| URL | Base URL of your Schreibwerkstatt, e.g. `https://schreibwerkstatt.example.com` |
| API token | `sw_…` token from the admin settings |
| Verify SSL certificate | Turn off for self-signed certificates |

Options: polling interval (default 60 s, 30–3600 s).

When the token is revoked or expires, Home Assistant asks for a new one (re-authentication) instead
of leaving every sensor unavailable. The entry is keyed by the server's `instance_id`, so a changed
host name only needs the URL updated — re-adding the integration with the new URL does that.

## What you get

| Device | Examples |
|---|---|
| **Schreibwerkstatt** | uptime, memory, database size, JS errors (24 h), pending registrations |
| Schreibwerkstatt Users | users per status, active users 24 h / 7 days |
| Schreibwerkstatt Content | books (all / with text), chapters, sections, characters, words, standard pages, characters per book and per person |
| Schreibwerkstatt Writing | writing / editing / dictation time today, net characters and words today, characters per writing hour |
| Schreibwerkstatt Jobs | running and queued jobs, finished / failed in 24 h |
| Schreibwerkstatt AI | cost today / this month / total, tokens per provider and model, Anthropic billing |
| Schreibwerkstatt Block merge | merge telemetry (diagnostic) |
| **one device per user** | writing time today, daily goal %, *daily goal reached*, characters and words (today and in stock), characters per writing hour, books, AI cost, last seen |

Breakdowns with many label combinations (cost per job type, cache tokens, job history per type,
devices per client version) are created disabled — enable the ones you want.

Three values are computed by the integration, by the same rules live and in the back-filled
history: **characters per book** (over books with text), **characters per person** (over people
with characters of their own, so readers do not pull it down) and **characters per writing hour**
(net characters today over writing time today, from 10 minutes of writing on).

Daily and monthly totals report `last_reset` (midnight / first of month in the server's time zone),
so long-term statistics restart correctly. Net characters and words today can fall (text deleted);
they are daily totals, so a chart's *change* per day is the day's net.

### History

The server keeps a snapshot of every book every evening. On every start the integration fetches
these days (`/metrics/history.json`, Schreibwerkstatt 4.21+) and writes them into the long-term
statistics of the matching sensors — characters, words and books in stock, net per day, writing /
editing / dictation time, per person and the computed averages and pace. Charts then show the whole
past instead of starting on the day of the set-up.

Only days before a sensor's first recorded statistic are written: what the recorder collected
itself is never overwritten, and later starts find nothing left to add. The last 365 days are daily,
older ones month-end values (the server thins its snapshots). Deleted books are gone from the
history too. Without the recorder, or with an older server, nothing happens.

User devices are named after the display name in Schreibwerkstatt (the e-mail if none is set) and
identified by the e-mail: when the name changes, the device is renamed and entities, entity IDs and
history stay.

### Dashboard

The integration ships a dashboard strategy that builds a complete dashboard from the entities that
actually exist — characters first (today, in stock, per book and person, pace), one section per
user seen in the last 14 days under *People* (the others in a compact list; daily goal gauge and AI
tiles only where they apply), daily token charts for the AI models used in the last
30 days (input and output apart), every model ever used under *Content & operations*, enabled
breakdowns under *Diagnostics*. No entity IDs to adapt: they depend on the users'
display names and your HA language, so the strategy asks the integration instead of guessing.

In **storage mode** (the HA default), the integration registers the strategy module as a Lovelace
resource on start-up — nothing to do. **Settings → Dashboards → Add dashboard → New dashboard from
scratch → ⋮ → Raw configuration editor**:

```yaml
strategy:
  type: custom:schreibwerkstatt
```

In **YAML mode** (rare), Lovelace resource lists are read-only and cannot be edited from an
integration, so you have to add the resource by hand. A warning is logged on every start-up with
the exact line to add:

```yaml
lovelace:
  mode: yaml
  resources:
    - url: /schreibwerkstatt/schreibwerkstatt-strategy.js?v=0.4.0
      type: module
```

Without the resource the dashboard renders only intermittently: the strategy module is fetched
fire-and-forget and races a 5 s timeout (HA frontend issue #52570), so on cold loads
Home Assistant reports *Timeout waiting for strategy element ll-strategy-dashboard-schreibwerkstatt
to be registered*. A hard refresh usually fixes it for that session, but the proper fix is the
resource entry — they are awaited, `add_extra_js_url` modules are not.

New users and models appear on the next reload of the dashboard. To customise it, use
**⋮ → Take control**: Home Assistant turns the generated dashboard into regular YAML with your
real entity IDs. See [examples/dashboard.yaml](examples/dashboard.yaml) for the options.

### Milestones

[![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fschreibwerkstatt%2Fhomeassistant%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fschreibwerkstatt%2Fmilestone.yaml)

The blueprint [milestone.yaml](blueprints/automation/schreibwerkstatt/milestone.yaml) runs your
actions whenever a counter passes a round mark — every 100,000 characters in stock, every 10,000
characters of one person. A restart or an outage does not count as passing one.

### Automation example

```yaml
automation:
  - alias: Writing goal reached
    triggers:
      - trigger: state
        entity_id: binary_sensor.anna_daily_goal_reached
        to: "on"
    actions:
      - action: notify.mobile_app_phone
        data:
          message: "Daily writing goal reached ✍️"
```

## Development

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
ruff check . && pytest
```

`tests/fixtures/metrics.json` is a real `/metrics.json` response generated by the server's collector;
the contract itself is documented in the server repository (`docs/metrics-api.md`, section
*JSON für Home Assistant*).

## License

MIT – see [LICENSE](LICENSE).
