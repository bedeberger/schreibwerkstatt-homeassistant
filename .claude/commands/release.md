---
description: Arbeitsstand committen, Version setzen, testen, Tag und GitHub-Release erstellen (HACS meldet das Update in Home Assistant)
argument-hint: "[patch|minor|major|x.y.z] [--draft] [--dry-run]"
allowed-tools: Bash(git *), Bash(gh *), Bash(.venv/bin/*), Bash(sed *), Bash(python3 *), Read, Write, Edit
---

# Release

Erzeugt aus dem aktuellen Stand ein GitHub-Release. **Das Release ist das, was
Home Assistant sieht:** HACS vergleicht die installierte Version mit dem neuesten
GitHub-Release dieses Repositories und zeigt dann unter *Einstellungen → Updates*
ein Update an, samt den Release-Notizen. Ein Tag ohne Release, ein Entwurf oder ein
Commit auf `main` allein lösen dort nichts aus.

Der Arbeitsstand wird mitgenommen: Was im Arbeitsverzeichnis liegt, ist nach
`/release` committet und auf `origin/main`, ohne Rückfrage. `--dry-run` ist der
einzige folgenlose Weg.

Argumente: `$ARGUMENTS`

- `patch` · `minor` · `major` · `x.y.z` — Version vorher erhöhen. Ohne Angabe
  wird die Version aus `manifest.json` genommen, wie sie ist (Normalfall nur beim
  allerersten Release).
- `--draft` — Release als Entwurf anlegen. HACS sieht Entwürfe **nicht**; das
  Update erscheint erst, wenn der Entwurf auf GitHub veröffentlicht wird.
- `--dry-run` — prüfen, testen und die Notizen zeigen, aber weder Version
  schreiben noch committen, pushen oder ein Release anlegen.

## Regeln

- **Einzige Versionsquelle ist `custom_components/schreibwerkstatt/manifest.json`
  → `version`.** Tag ist immer `v<version>`, Release-Titel ebenso. Weicht die
  Manifest-Version vom Tag ab, zeigt HA nach dem Update die falsche Version an.
- **Ohne Rückfrage**, sobald die Prüfungen grün sind. Gestoppt wird nur bei
  einem Fehlschlag, kein `--force`, kein `push -f`.
- **Ein bestehender Tag wird nie überschrieben.** Gleiche Version zweimal heisst
  Abbruch mit Hinweis auf ein Bump-Argument.
- Wird nach dem Versions-Bump abgebrochen, den Bump zurücknehmen
  (`git checkout -- custom_components/schreibwerkstatt/manifest.json`).
- **Das Repository ist öffentlich.** In Commit, Tag und Notizen keine Token,
  keine echten Hostnamen oder IPs, keine lokalen Pfade; Beispieladresse ist immer
  `schreibwerkstatt.example.com`. Weil `git add -A` alles mitnimmt, gilt das auch
  für den Inhalt des Commits (Schritt 1).

## 1. Vorprüfungen

```bash
git rev-parse --abbrev-ref HEAD                # erwartet: main
git fetch --tags --quiet origin
git rev-list --left-right --count @{u}...HEAD  # erwartet: 0 <n>
gh auth status
test -x .venv/bin/pytest                       # sonst VS-Code-Task „Setup: venv + Testabhängigkeiten"
git status --porcelain --untracked-files=all
git diff HEAD --stat
```

Abbruchgründe: nicht auf `main` (nachfragen), Rückstand gegenüber `origin/main`
(erst `git pull --ff-only`), `gh` nicht angemeldet, ungemergte Pfade, keine `.venv`.

Ein voller Arbeitsstand ist **kein** Abbruchgrund. Aber jede Datei benennen und
nicht getrackte Dateien (`??`, die `git diff` nicht zeigt) einzeln mit `Read`
ansehen. Abbrechen, wenn etwas dabei ist, das nicht in ein öffentliches Repository
gehört: Token ausserhalb der Test-Attrappen, echte Hostnamen, `.env`-Reste, Logs,
lokale HA-Konfiguration (`config/`, `secrets.yaml`, `.storage/`), Screenshots mit
echten Daten. Im Zweifel fragen, nicht committen.

## 2. Version festlegen

Aktuelle Version lesen:

```bash
python3 -c "import json;print(json.load(open('custom_components/schreibwerkstatt/manifest.json'))['version'])"
```

Bei Bump-Argument die neue Version berechnen (`patch` 0.1.0 → 0.1.1, `minor`
→ 0.2.0, `major` → 1.0.0, `x.y.z` als Semver validieren) und **nur die
Versionszeile** ersetzen, damit die übrige Formatierung des Manifests bleibt:

```bash
sed -i -E 's/("version": ")[^"]+(")/\1<neu>\2/' custom_components/schreibwerkstatt/manifest.json
```

Bei `--dry-run` nicht schreiben, nur die neue Nummer merken.

Tag muss frei sein, lokal **und** auf `origin`:

```bash
git tag -l "v<version>"
git ls-remote --tags origin "refs/tags/v<version>"
```

Beides leer, sonst Abbruch.

## 3. Prüfungen (wie CI)

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q
python3 -m json.tool custom_components/schreibwerkstatt/manifest.json > /dev/null
```

Ein Fehlschlag beendet den Release. Ausgabe zeigen, nichts umdeuten, Tests nicht
anpassen. Hassfest und die HACS-Validierung laufen nur in GitHub Actions
(`validate.yml`); nach dem Push in Schritt 7 deren Ergebnis prüfen.

## 4. Notizen schreiben

Quellen: `git log --pretty=format:'%s%n%b' <letzter-tag>..HEAD` (beim ersten
Release: alle Commits) **und** der Arbeitsstand aus Schritt 1, denn der wird erst
in Schritt 6 committet und steht in keinem Log.

Die Notizen erscheinen in Home Assistant im Update-Dialog. Leser ist jemand, der
die Integration benutzt: was sich an Sensoren, Entitäten, Einrichtung oder
Verhalten ändert. Interne Umbauten, Tests, CI und Editor-Konfiguration weglassen.
Englisch, wie README und Oberfläche des Repositories. Aufbau:

```markdown
<one sentence on what this version is about>

### Added
- …

### Changed
- …

### Fixed
- …
```

Leere Abschnitte weglassen. **Immer ausdrücklich nennen** (unter einer eigenen
Überschrift `### Breaking changes` ganz oben): umbenannte oder entfernte
Entitäten bzw. `unique_id`s, geänderte Konfigurationsfelder, eine angehobene
Mindestversion in `hacs.json`, alles, was nach dem Update einen Handgriff in HA
verlangt (Neustart reicht nicht, Integration neu einrichten, Automationen
anpassen). Ein Neustart von HA nach dem Update ist immer nötig und muss nicht
erwähnt werden.

Reiner Wartungs-Release: ein ehrlicher Satz („Maintenance release, no changes to
entities or setup.").

Datei in den Scratchpad schreiben, nicht ins Repository.

## 5. Zusammenfassung

Zeigen, nicht fragen: alte → neue Version, Testergebnis, Zieltag, `--draft`
ja/nein, die Dateien, die mit in den Commit gehen, und die fertigen Notizen.

Bei `--dry-run` hier enden, mit dem Hinweis, dass weder Version noch Commit, Tag
oder Release geschrieben wurden.

## 6. Veröffentlichen

```bash
git add -A
git status --short

git commit -m "$(cat <<'MSG'
Release v<version>

<ein bis drei Zeilen, was in dieser Version steckt>

Co-Authored-By: <aktueller Modellname aus den Harness-Vorgaben> <noreply@anthropic.com>
MSG
)"

git tag -a "v<version>" -m "v<version>"
git push origin main
git push origin "v<version>"
```

Nichts zu committen (leerer Stand, kein Bump, also erster Release): Commit
überspringen und `HEAD` taggen. Keinen `--allow-empty`-Commit.

Vor dem Release verifizieren: `git ls-remote --tags origin v<version>` liefert
eine Zeile, und `git rev-parse v<version>^{commit}` gleicht `git rev-parse HEAD`.
Sonst stoppen.

```bash
gh release create "v<version>" \
  --title "v<version>" \
  --notes-file "<scratchpad>/release-notes-<version>.md" \
  --latest
  # bei --draft zusätzlich: --draft
```

Kein ZIP-Anhang: HACS lädt den Ordner `custom_components/schreibwerkstatt` aus dem
getaggten Stand.

Scheitert `gh release create`, nachdem Tag und Push durch sind: sagen und den
Befehl zum Nachholen ausgeben. Tag nicht löschen, Push nicht zurückdrehen.

## 7. Verifikation

```bash
git status --porcelain                       # leer
git log origin/main -1 --oneline             # Release-Commit
gh release view "v<version>" --json tagName,url,isDraft
gh run list --branch main --limit 4          # Tests + Validate für den Release-Commit
```

Laufen die Actions noch, das sagen (nicht warten). Ist eine bereits rot, das
deutlich melden: Das Release ist trotzdem draussen und HACS bietet es an.

## 8. Abschluss

Melden: alte → neue Version, Commit-Hash, Tag, Release-URL, welche Dateien der
Commit mitgenommen hat, Stand der Actions. Dazu für Home Assistant:

- HACS prüft nicht sofort. Wer das Update gleich sehen will: in HACS beim
  Repository *Schreibwerkstatt* → ⋮ → **Update information**. Danach erscheint es
  unter *Einstellungen → Updates*.
- Nach dem Installieren Home Assistant neu starten.
- Bei `--draft`: in HA erscheint nichts, bis der Entwurf auf GitHub
  veröffentlicht ist.
