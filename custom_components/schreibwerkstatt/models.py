"""Parsed view of the /metrics.json document."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

# Labels that identify a user; they select the device, not the entity name.
USER_LABELS = ("user", "user_name")
# Labels that describe rather than identify: a renamed user keeps their entities.
DESCRIPTIVE_LABELS = ("user_name",)


@dataclass(frozen=True, slots=True)
class Metric:
    """Description of one metric, as delivered by the server."""

    name: str
    group: str
    title: dict[str, str]
    unit: str | None
    device_class: str | None
    state_class: str | None
    reset: str | None
    icon: str | None
    diagnostic: bool
    enabled_default: bool
    entity: bool
    per_user: bool

    def title_for(self, lang: str) -> str:
        """Display name in the given language (de/en), falling back to the key."""
        return self.title.get(lang) or self.title.get("en") or self.title.get("de") or self.name


@dataclass(frozen=True, slots=True)
class Sample:
    """One value of a metric for one label combination."""

    key: str
    metric: Metric
    labels: dict[str, str]
    value: float

    @property
    def user(self) -> str | None:
        """E-mail of the user this sample belongs to (per-user metrics only)."""
        return self.labels.get("user")

    @property
    def name_labels(self) -> list[str]:
        """Label values that distinguish entities of the same metric on one device."""
        return [v for k, v in sorted(self.labels.items()) if k not in USER_LABELS and v]


def _derived(name: str, group: str, de: str, en: str, icon: str) -> Metric:
    return Metric(
        name=name,
        group=group,
        title={"de": de, "en": en},
        unit=None,
        device_class=None,
        state_class="measurement",
        reset=None,
        icon=icon,
        diagnostic=False,
        enabled_default=True,
        entity=True,
        per_user=group == "user",
    )


# Computed by the integration (derive) from what the server reports.
CHARS_PER_BOOK = _derived(
    "sw_chars_per_book", "content", "Zeichen pro Buch", "Characters per book", "mdi:book-open-page-variant"
)
CHARS_PER_AUTHOR = _derived(
    "sw_chars_per_author", "content", "Zeichen pro Person", "Characters per person", "mdi:account-edit"
)
_PACE = ("Zeichen pro Schreibstunde", "Characters per writing hour", "mdi:speedometer")
CHARS_PER_HOUR = _derived("sw_chars_per_hour", "writing", *_PACE)
USER_CHARS_PER_HOUR = _derived("sw_user_chars_per_hour", "user", *_PACE)
# Below this the pace is noise: two sentences in one minute make 6000 characters an hour.
MIN_WRITING_SECONDS = 600

type Values = Mapping[str, tuple[dict[str, str], float]]


def _per_hour(chars: float | None, seconds: float | None) -> float | None:
    if chars is None or seconds is None or seconds < MIN_WRITING_SECONDS:
        return None
    return round(chars / seconds * 3600)


def derive(values: Values) -> list[tuple[Metric, dict[str, str], float]]:
    """Values the server does not report, from sample key → (labels, value).

    Works on one poll as on one day of history, so live values and the imported
    past follow the same rules:
    - per book: over books with text (servers before sw_books_written: all books);
    - per person: over people with characters of their own, so someone who only
      reads along does not pull the average down;
    - per writing hour: net characters today over writing time today, from
      MIN_WRITING_SECONDS on.
    """

    def get(key: str) -> float | None:
        hit = values.get(key)
        return hit[1] if hit else None

    out: list[tuple[Metric, dict[str, str], float]] = []
    chars = get("sw_chars")
    books = get("sw_books_written")
    if books is None:
        books = get("sw_books")
    if chars is not None and books:
        out.append((CHARS_PER_BOOK, {}, round(chars / books)))
    own = [v for k, (_, v) in values.items() if k.startswith("sw_user_chars|") and v > 0]
    if own:
        out.append((CHARS_PER_AUTHOR, {}, round(sum(own) / len(own))))
    pace = _per_hour(get("sw_chars_today"), get("sw_writing_seconds_today"))
    if pace is not None:
        out.append((CHARS_PER_HOUR, {}, pace))
    for key, (labels, seconds) in values.items():
        if key.startswith("sw_user_writing_seconds_today|"):
            pace = _per_hour(get(sample_key("sw_user_chars_today", labels)), seconds)
            if pace is not None:
                out.append((USER_CHARS_PER_HOUR, labels, pace))
    return out


def sample_key(name: str, labels: dict[str, str]) -> str:
    """Stable identity of a sample: metric name plus its sorted identifying labels."""
    keys = sorted(k for k in labels if k not in DESCRIPTIVE_LABELS)
    if not keys:
        return name
    return name + "|" + "|".join(f"{k}={labels[k]}" for k in keys)


@dataclass(slots=True)
class MetricsData:
    """Everything one poll returned."""

    instance_id: str | None
    version: str | None
    timezone: str
    includes_users: bool
    samples: dict[str, Sample] = field(default_factory=dict)
    users: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> MetricsData:
        """Build from the server document; unknown fields are ignored."""
        data = cls(
            instance_id=raw.get("instance_id"),
            version=raw.get("version"),
            timezone=raw.get("timezone") or "UTC",
            includes_users=bool(raw.get("includes_users")),
        )
        for m in raw.get("metrics", []):
            metric = Metric(
                name=m["name"],
                group=m.get("group") or "server",
                title=m.get("title") or {},
                unit=m.get("unit"),
                device_class=m.get("device_class"),
                state_class=m.get("state_class"),
                reset=m.get("reset"),
                icon=m.get("icon"),
                diagnostic=bool(m.get("diagnostic")),
                enabled_default=m.get("enabled_default", True) is not False,
                entity=m.get("entity", True) is not False,
                per_user=bool(m.get("per_user")),
            )
            for s in m.get("samples", []):
                labels = {str(k): str(v) for k, v in (s.get("labels") or {}).items()}
                key = sample_key(metric.name, labels)
                data.samples[key] = Sample(key, metric, labels, float(s.get("value") or 0))
                if metric.per_user and labels.get("user"):
                    data.users[labels["user"]] = labels.get("user_name") or labels["user"]
        for metric, labels, value in derive({k: (v.labels, v.value) for k, v in data.samples.items()}):
            key = sample_key(metric.name, labels)
            data.samples[key] = Sample(key, metric, labels, float(value))
        return data

    def label_value(self, name: str, label: str) -> str | None:
        """First value of `label` among the samples of metric `name`."""
        for sample in self.samples.values():
            if sample.metric.name == name and label in sample.labels:
                return sample.labels[label]
        return None
