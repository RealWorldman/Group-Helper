# Gilden-Berufe-/Rezept-Bot — WoW: Forever

## Context

**Problem:** In der Gilde weiß niemand zuverlässig, wer welchen Beruf hat und wer welche seltenen Rezepte besitzt. „Wer kann mir +35 Beweglichkeit auf die Waffe machen?" wird per Zuruf im Chat gelöst — unzuverlässig und endlos wiederholt.

**Ziel:** Ein Discord-Bot, in dem Mitglieder Charaktere, Berufe und seltene Rezepte erfassen, und in dem jeder per deutscher Frage herausfindet, wer was herstellen kann.

**Spiel: World of Warcraft: Forever** (Blizzard Classic+). Beta 17.09.–21.10.2026, **Release 4. November 2026**. Level-Cap 60, 12 Berufe (9 primär, 3 sekundär), **600+ neue Rezepte**, neue Berufs-Mechaniken (Campsite-Rezepte, Blueprints aus Dungeon-Bossen).

### Scope: nur primäre Berufe

**Sekundärberufe (Kochkunst, Erste Hilfe, Angeln) bleiben außen vor** — die kann jeder gleichzeitig lernen, also beantwortet „wer kann das?" sich von selbst. Das halbiert nahezu den Erfassungsaufwand pro Charakter.

Von den 9 primären Berufen haben nur 7 überhaupt Rezepte: **Alchemie, Schmiedekunst, Verzauberkunst, Ingenieurskunst, Lederverarbeitung, Bergbau (Schmelzen), Schneiderei.** Kräuterkunde und Kürschnerei sind reine Sammelberufe — sie werden zwar am Charakter erfasst (für „wer kann mir Leder machen?"), haben aber keine Rezepteinträge.

> ⚠️ **Eine Einschränkung, die du kennen solltest:** In Classic sind ein paar Kochrezepte durchaus raid-relevant und *nicht* beim Lehrer lernbar — Chimaerokkoteletts, Gewürzte Wüstenknödel und Ähnliches waren klassische Buff-Food-Engpässe. Forever hat laut den Guides zusätzlich eine Kochkunst-Überarbeitung. Es kann also sein, dass dir hier später etwas fehlt.
>
> Deshalb ist der Ausschluss **eine Konfigurationszeile, kein Schema-Entwurf**: `config.INCLUDED_PROFESSION_KEYS`. Das Datenmodell kennt Sekundärberufe ganz normal; der Scraper überspringt ihre Kategorien und die Commands filtern darauf. Kochkunst nachträglich dazuzunehmen ist ein Config-Eintrag plus ein Katalog-Update — kein Umbau.

### Was das gegenüber einem Classic-Projekt grundlegend ändert

| Bei Classic möglich | Bei Forever (Stand 20.09.2026) |
|---|---|
| Blizzard Game Data API für Item-Namen (DE+EN) | **Existiert nicht.** Das Blizzard-API-Forum wartet seit Tagen unbeantwortet auf Forever-Endpoints. |
| Privatserver-DB-Dump (cmangos) als Quelle | **Unbrauchbar** — Forever hat massiv geänderte und neue Rezepte. |
| Katalog einmalig generieren und einchecken | **Bewegliches Ziel** — Beta → Release → Folge-Content. |
| Katalog ist vollständig | **Systematisch unvollständig.** Beta-Cap ist Level 30, alles darüber ist noch nicht auffindbar. Wowhead füllt die DB gerade erst per Crowdsourcing. |
| Trainer-Filter als exakter DB-Join | Nur heuristisch aus crowdsourcten Wowhead-Quellendaten. |

**Daraus folgen die drei tragenden Entscheidungen dieses Plans:**

1. **Der Katalog ist ein lebendes Artefakt**, kein Seed: wöchentlicher Auto-Scrape + `/admin katalog-update`, Diff-Report in einen Admin-Channel, versionierte Snapshots, niemals Löschen.
2. **Provisorische Rezepte sind ein First-Class-Feature.** Wer ein Rezept besitzt, das der Katalog nicht kennt, meldet es per Freitext — es ist sofort abfragbar und wird beim nächsten Katalog-Update automatisch mit dem echten Eintrag verschmolzen.
3. **Der Trainer-Filter ist weich.** Alles wird importiert, Trainer-Rezepte werden nur ausgeblendet. Ein Flag lässt sich umschalten; ein Fehlurteil der Quelle löscht keine Daten.

**Zeitplan:** Maschinerie jetzt bauen und gegen Beta-Daten testen. **Die Gilde onboardet ab dem 4.11.** — niemand erfasst Daten, die bei Release ungültig werden. Das sind **~6,5 Wochen** bis zum Stichtag.

**Rahmen:** Bot auf **Raspberry Pi 5** im Heimnetz. LLM in **LM Studio** auf separatem PC (16 GB VRAM), **nicht durchgehend an** → der Bot muss ohne LLM voll funktionieren. Das LLM ist Komfort-Layer, nicht Fundament.

---

## Leitprinzip

> **Das LLM extrahiert nur die Absicht. Es sucht keine Rezepte und schreibt kein SQL.**

```
Frage
 ├─1. Rule-Fast-Path   (Regex: "wer ist <beruf>", "wer kann <x>")   ← kein LLM
 ├─2. LLM → Intent-JSON (nur wenn 1 nicht greift UND LLM erreichbar)
 ├─3. Entity-Resolution (FTS5 + Alias + RapidFuzz)                  ← NIE LLM
 ├─4. SQL-Builder: handgeschriebene parametrisierte Queries         ← NIE LLM
 └─5. Rendering (Embed + Monospace-Tabelle)
```

Schritte 1, 3, 4, 5 sind deterministisch. **Der Fallback bei offline-LLM ist derselbe Code-Pfad ohne Schritt 2** — kein zweiter, schlechter getesteter Notfallpfad.

Das Kernproblem ist **nicht** SQL-Generierung, sondern Entity-Resolution: `"+35 Beweglichkeit auf Waffen"` → die richtige Formel. Und, genauso wichtig: Nutzer fragen nach dem **hergestellten Gegenstand** („Wollstofftasche"), nicht nach dem Rezeptnamen („Muster: Wollstofftasche"). Beide Namen müssen durchsuchbar sein.

### Zweisprachigkeit: Deutsch und Englisch sind gleichwertig

> **Jede Suche muss in beiden Sprachen treffen.** „Wollstofftasche" und „Woolen Bag" führen zum selben Rezept — unabhängig davon, welche Client-Sprache der Fragende spielt.

Das ist keine Kür: In einer deutschen Gilde spielt regelmäßig ein Teil mit englischem Client, Guides und Wowhead-Links sind englisch, und Kürzel im Chat mischen ohnehin beides („den Bottomless Bag", „35 Agi auf Waffe").

Was daraus folgt, quer durch den Stack:

- **Katalog:** Jeder Scrape-Durchlauf läuft zweimal — `/forever/...` und `/forever/de/...`, Join über die `spell_id`. Beide Namen werden gespeichert, keiner ist der „richtige".
- **Datenmodell:** `name_de`/`name_en`, `display_de`/`display_en` und `crafted_name_de`/`crafted_name_en` sind bereits paarweise angelegt; die normalisierten Spalten (`*_norm`) ebenso. Kein Feld darf einsprachig werden.
- **FTS5:** Der Index umfasst alle vier Namensspalten (`display_de, display_en, crafted_de, crafted_en`) plus `alias_blob`. Eine einzige Query durchsucht damit beide Sprachen gleichzeitig — kein Sprach-Switch, keine Spracherkennung an der Frage.
- **Resolver:** Die Normalisierung (Umlaut-Folding `ä→ae`, `ß→ss`) und die Slot-Synonym-Map sind ausdrücklich sprachübergreifend gebaut: `tasche↔bag`, `waffe↔weapon`, `umhang↔cloak↔mantel`. Aliase tragen ein `lang`-Feld, werden bei der Suche aber **nicht** danach gefiltert.
- **Autocomplete:** zeigt beide Namen in einem Eintrag (`Wollstofftasche / Woolen Bag`), damit beide Tippweisen sichtbar zum Ziel führen.
- **Ausgabe:** Antwortsprache ist Deutsch. Der englische Name steht ergänzend dabei, wo er in die Zeile passt — der Bot übersetzt nicht, er zeigt beide Beschriftungen desselben Gegenstands.
- **Fallback:** Fehlt ein Name in einer Sprache, wird der vorhandene angezeigt. Das gilt in **beide** Richtungen, nicht nur DE→EN.

---

## Datenquelle: Wowhead-Scraping

Wowhead ist derzeit die **einzige** automatisierbare Quelle. Bestätigte URL-Struktur:

```
https://www.wowhead.com/forever/items/recipes          # Rezept-Items, Filter pro Beruf
https://www.wowhead.com/forever/de/items/recipes       # deutsche Variante (Lokalisierung in Arbeit)
```

Bestätigte Berufs-Kategorien im Filter — **fett = im Scope**:

**Alchemy Recipes**, **Blacksmithing Plans**, **Enchanting Formulae**, **Engineering Schematics**, **Leatherworking Patterns**, **Mining Guides**, **Tailoring Patterns** · ~~Cooking Recipes~~, ~~First Aid Books~~, ~~Fishing Books~~ (sekundär) · „Books" ist unklar und in M0 zu prüfen — vermutlich ein Sammelposten, der Einträge aus mehreren Berufen enthält.

Gescrapt werden nur die sieben Kategorien im Scope. Das reduziert Requests, Katalogumfang und Erfassungsaufwand in einem Zug.

### Zwei Scrape-Ziele, nicht eines

| Ziel | Liefert | Wofür |
|---|---|---|
| **Rezept-Items** `/forever/items/recipes/<kategorie>` | item_id, Rezeptname, Qualität, benötigter Skill, Quelle | Was erfasst wird, Trainer-Filter |
| **Berufs-Zauber** `/forever/spells/professions/<beruf>` | spell_id, **hergestellter Gegenstand**, Skill-Farbstufen | Der Name, nach dem Nutzer tatsächlich fragen |

Der Join beider Listen ergibt `Rezept → Herstellungsprodukt`. **Ohne das zweite Ziel scheitert die Beispielfrage nach der Wollstofftasche.**

### Technischer Ansatz (M0-Spike, in dieser Reihenfolge testen)

1. **Listing-Seiten mit eingebettetem `Listview`-Datenarray.** Wowhead-Listen liefern die komplette gefilterte Liste als JS-Array in einer einzigen Antwort — ein Request pro Beruf statt einer pro Item. Das ist der mit Abstand schonendste Weg und der Primärversuch.
2. **Tooltip-/XML-Endpoint** pro Item, falls die Listings zu wenig Felder haben (Quelle, Herstellungsprodukt). Gecacht, ein Request pro Item, nur einmalig und bei Diffs.
3. **Zwei Durchläufe für Lokalisierung**: identische Requests gegen `/forever/...` und `/forever/de/...`, Join über `item_id`.

**Fehlt ein Name in einer Sprache, wird der andere angezeigt** (`display_de` leer → Fallback `display_en` und umgekehrt). Der Fallback bleibt als Sicherungsnetz, ist aber nach dem M0-Spike nicht der Normalfall: Für Schneiderei sind **477 von 477 Einträgen übersetzt, einschließlich der neuen Forever-Rezepte** — die deutsche Lokalisierung ist weiter als beim Verfassen dieses Plans angenommen. Für die übrigen Berufe ist das noch zu prüfen. Belege in [tools/catalog_sources.md](tools/catalog_sources.md).

> ⚠️ **Rechtlicher Hinweis, ehrlich:** Wowheads Nutzungsbedingungen schränken automatisierten Zugriff ein. Für ein privates Gilden-Tool ist das eine Grauzone, kein Freibrief. Mitigation: **max. 1 Request/Sekunde**, aussagekräftiger `User-Agent` mit Kontaktadresse, `ETag`/`If-Modified-Since`, aggressives Caching, **keine öffentliche Weiterverbreitung des Datensatzes**. Wenn Wowhead blockt oder du das nicht willst: In-Game-Addon-Export als Ersatzquelle (siehe *Offene Optionen*).

### Katalog-Artefakte

```
profession-helper-app/tools/scrape_wowhead.py       # Scraper (Listings -> Roh-JSON)
profession-helper-app/tools/build_catalog.py        # Roh -> normalisierter Katalog + Diff
profession-helper-app/tools/catalog_sources.md      # Endpoints, Reproduktion, Rate-Limits
profession-helper-app/data/catalog/current.json     # aktiver Katalog (catalog_version + content_hash)
profession-helper-app/data/catalog/snapshots/forever-2026-11-04.json   # jede Version bleibt
profession-helper-app/data/catalog/aliases.de.yaml  # handkuratiert
profession-helper-app/data/catalog/overrides.yaml   # manuelle Korrekturen, überschreiben den Scrape
```

`overrides.yaml` ist wichtig: Wenn Wowhead ein Rezept falsch als Trainer-Rezept führt, korrigierst du es dort — und die Korrektur überlebt jeden Re-Scrape.

### Update-Zyklus

- `@tasks.loop(hours=168)` wöchentlich + `/admin katalog-update` für sofort (wichtig rund um den Release)
- Import ist **Upsert, niemals Delete**. Entfallene Rezepte nur `is_active = False`, damit `character_recipes` nie verwaist.
- Diff-Report in den Admin-Channel: *„+14 neue Rezepte (Schneiderei 6, Verzauberkunst 3 …), 3 Namen geändert, 2 deutsche Namen ergänzt, 1 provisorisches Rezept automatisch zugeordnet"*
- **Nie live auf die produktive DB scrapen:** Scrape → Snapshot-Datei → Validierung (Plausibilitätscheck: Rezeptzahl darf nicht um >20 % fallen) → erst dann Import. Ein kaputter Scrape darf den Katalog nicht leeren.

**Professionen aus den Daten ableiten, nicht hartkodieren.** Forever hat eigene Berufsmechaniken und möglicherweise einen weiteren Beruf — eine feste Liste im Code wäre schon bei Release falsch. Der Scraper entdeckt die Kategorien, `config.INCLUDED_PROFESSION_KEYS` entscheidet, welche davon importiert werden. Neu auftauchende Berufe landen im Diff-Report und werden bewusst freigeschaltet, statt stillschweigend durchzurutschen.

---

## Datenmodell

Eigene DB `profession_helper.db`, SQLAlchemy 2.0 mit `class Base(DeclarativeBase)`.

```
professions            id PK, key, name_de, name_en, is_primary, has_recipes, is_included,
                       wowhead_category
guilds                 id PK (BigInteger = Discord guild id), name, created_at
members                id PK, guild_id FK, discord_user_id BigInteger, display_name, created_at
                       UNIQUE(guild_id, discord_user_id)
characters             id PK, member_id FK, guild_id FK,
                       name, name_norm, realm, faction, class, level,
                       is_main, is_active, last_confirmed_at, deleted_at, created_at, updated_at
                       UNIQUE(guild_id, name_norm, realm)
character_professions  id PK, character_id FK, profession_id FK,
                       skill_level, skill_max, specialization, updated_at
                       UNIQUE(character_id, profession_id)
recipes                item_id PK, spell_id, profession_id FK,
                       name_de, name_en, display_de, display_en, display_de_norm, display_en_norm,
                       crafted_item_id, crafted_name_de, crafted_name_en, crafted_norm,
                       required_skill, source_type, source_note, quality, faction_restriction,
                       is_trainer_taught, is_hidden, is_active,
                       is_provisional, provisional_raw_name, reported_by_member_id, merged_into_item_id,
                       catalog_version, first_seen_at, last_seen_at
recipe_aliases         id PK, recipe_item_id FK, alias, alias_norm, lang,
                       source Enum('seed','generated','user'), added_by_member_id, created_at
                       UNIQUE(recipe_item_id, alias_norm)
character_recipes      id PK, character_id FK, recipe_item_id FK, added_by_member_id, created_at
                       UNIQUE(character_id, recipe_item_id)
alias_suggestions      id PK, raw_query, resolved_recipe_item_id, confirm_count, created_at, last_seen_at
catalog_runs           id PK, started_at, finished_at, status, recipes_total, added, changed,
                       deactivated, merged, error
query_log              id PK, guild_id, member_id, question, intent_json,
                       mode Enum('rule','llm_intent','llm_sql','deterministic'),
                       duration_ms, result_count, created_at
schema_version         version PK, applied_at
```

**Discord-Snowflakes durchgängig `BigInteger`** — [models.py](../group-helper-app/services/models.py) nutzt `Integer`; SQLite verzeiht das, wir erben den Fehler nicht.

### Provisorische Rezepte — der Mechanismus

- **Negative `item_id`** (`-1, -2, …`) für provisorische Einträge. Echte Wowhead-IDs sind positiv → keine Kollision möglich, und der Merge ist ein simples FK-Update.
- Anlage über `/rezept melden char: name:<Freitext> beruf:<Choice>`. Sofort in `character_recipes` nutzbar und abfragbar.
- **Auto-Merge beim Katalog-Update:** jeder provisorische Eintrag wird gegen neue Katalogeinträge gematcht (normalisierter Name, DE+EN, plus `crafted_*`). Score > 0.88 → `character_recipes.recipe_item_id` umhängen, provisorischen Eintrag `merged_into_item_id` setzen, Melder per DM informieren.
- Score 0.6–0.88 → **Admin-Review-Queue**, als Nachricht mit `Bestätigen`/`Verwerfen`-Buttons in den Admin-Channel. Keine stille Fehlzuordnung.
- In allen Ausgaben sind provisorische Rezepte mit `*` markiert und im Footer erklärt.

### Indizes

- `ix_charprof_prof_skill (profession_id, skill_level DESC)` → „Wer ist Verzauberer?"
- `ix_charrecipe_recipe (recipe_item_id)` → „Wer kann X?"
- `ix_characters_guild_active (guild_id, is_active)`, `ix_characters_member (member_id)`
- `ix_recipe_aliases_norm (alias_norm)`, `ix_recipes_profession (profession_id, is_active, is_hidden)`

**FTS5:** `recipes_fts` als External-Content-Table über `recipes`, Spalten `display_de, display_en, crafted_de, crafted_en, alias_blob`, Tokenizer `unicode61 remove_diacritics 2`.

**Soft-Delete:** Charaktere nie löschen, nur `is_active = False`. `last_confirmed_at` treibt einen monatlichen Reminder; Chars ohne Bestätigung seit >90 Tagen im Autocomplete mit „⚠" markiert.

**Twinks:** `members` 1:n `characters`. Ergebnisse nach *Member* gruppieren („@Yves — Mainhand (Verzauberkunst 300), Bankalt"), `is_main` steuert die Sortierung.

---

## Discord-Commands

Alle deutsch, ephemeral, als `app_commands.Group`.

```
/char anlegen name: realm:<Choice> klasse:<Choice> fraktion:<Choice> [level:]
/char liste [spieler:]   /char main   /char inaktiv   /char bestaetigen
/beruf setzen char:<AC> beruf:<Choice> skill:<int> [spez:<Choice>]
/beruf entfernen char:<AC> beruf:<AC>

/rezept hinzufuegen char:<AC> rezept:<AC>      # Hauptweg, Einzelerfassung
/rezept erfassen   char:<AC> beruf:<Choice>    # Massenerfassung-Wizard (Onboarding!)
/rezept melden     char:<AC> name:<Freitext> beruf:<Choice>   # nicht im Katalog
/rezept meine      char:<AC>
/rezept entfernen  char:<AC> rezept:<AC>
/rezept alias      rezept:<AC> alias:<text>

/wer beruf beruf:<Choice> [min_skill:]         # deterministisch, immer verfügbar
/wer kann  rezept:<AC>
/suche     begriff:<text>
/frage     text:<...>                           # LLM-Komfort, degradiert automatisch

/admin katalog-update   /admin katalog-status   /admin rezept-sichtbarkeit
/admin char-uebertragen /admin export
```

**Zwei unterschiedliche Berufslisten, bewusst:** `/beruf setzen` bietet **alle 9 primären** Berufe an — auch Kräuterkunde und Kürschnerei, damit „wer kann mir Leder machen?" beantwortbar bleibt. Die Rezept-Commands bieten nur die **7 Berufe mit Rezepten**. Beide Listen kommen aus der `professions`-Tabelle (`is_primary` bzw. `has_recipes`), nicht aus Konstanten im Code.

### Rezept-Erfassung

**Weg A (Hauptweg): Autocomplete statt Select-Menü.** Der Autocomplete-Callback für `rezept` liest über `interaction.namespace.char` den gewählten Charakter, filtert auf **dessen Berufe**, blendet Erfasstes und `is_hidden` aus, sucht über DE + EN + **Herstellungsprodukt** + Aliase. `Choice.value = str(item_id)`.
→ **Umgeht das 25-Options-Limit vollständig**, zustandslos, kein Timeout-Problem.

**Weg B (Onboarding-Massenerfassung): `RecipeWizardView`.** Ab dem 4.11. onboardet die halbe Gilde in derselben Woche — dieser Weg ist deshalb **release-kritisch, nicht optional**.
- Row 0: `Select`, bis 25 Rezepte der Seite, `min_values=0, max_values=25`, Erfasstes mit `default=True` → Hinzufügen und Entfernen sind dieselbe Geste.
- Row 1: `◀ Zurück` · `Seite 2/4` (disabled) · `Weiter ▶` · `🔎 Filtern` · `✅ Fertig`
- `🔎 Filtern` → Modal mit einem Feld, reduziert die Seite auf meist <25 Einträge.
- **Speichern im Select-Callback pro Seite als Diff**, nicht erst bei „Fertig" → View-Timeout ist harmlos.
- Sortierung nach `required_skill` aufsteigend (Reihenfolge wie im Spiel).
- `timeout=600` (sicher unter dem 15-Min-Interaction-Token); `on_timeout` disabled alles und weist auf Neuaufruf hin.

**Berechtigungen:** Jeder bearbeitet nur eigene Charaktere (`member.discord_user_id == interaction.user.id`); konfigurierbare Admin-Rolle darf alles.

---

## Query-Pipeline

### Intent-Schema

Flach, **alle Felder `required` und nullable** (Grammar-Sampling mag das lieber als optional), `enum` wo möglich:

```jsonc
{
  "intent": { "enum": ["who_has_profession","who_can_craft","what_can_character_craft",
                       "list_recipes","character_info","unknown"] },
  "profession":     "string|null",   // enum, zur Laufzeit aus professions-Tabelle gefüllt
  "craft_query":    "string|null",   // WÖRTLICHER Ausschnitt der Frage
  "character_name": "string|null",
  "min_skill":      "integer|null",
  "faction":        { "enum": [null,"alliance","horde"] },
  "confidence":     "number"
}
```

`craft_query` ist ein **wörtlicher Ausschnitt der Nutzerfrage** — das Modell darf nicht übersetzen und keine Item-Namen erfinden. Das übernimmt der Resolver. Das `profession`-Enum wird beim Start aus der DB generiert, nicht hartkodiert.

### LM Studio

`POST {LMSTUDIO_BASE_URL}/chat/completions` mit `response_format: {type:"json_schema", json_schema:{…, strict:true}}`, `temperature: 0`, `max_tokens: 200`.

LM Studio erzwingt das Schema bei GGUF über **grammar-based sampling (llama.cpp)** → syntaktisch gültiges JSON ist garantiert. Das ist für 7–14B entscheidend.

⚠️ **`/v1/chat/completions` verwenden, nicht `/v1/responses`** — dort gibt es einen offenen Bug, bei dem trotz `json_schema` Markdown zurückkommt. Modelle <7B können Structured Output oft nicht; bei 16 GB VRAM ist ein 14B in Q4_K_M mit 8k Kontext der Sweet Spot.

### Entity-Resolution (`services/resolver.py`) — das Kernstück

1. **Normalisierung** (`utils/textnorm.py`): lowercase, Umlaut-Folding (ä→ae, ß→ss), Interpunktion weg, „+35"→„35", Stemming-Lite für „verzauber(t|ung|en|er)", plus **Slot-Synonym-Map**: `waffe↔weapon`, `brust↔bruststück↔chest`, `armschiene↔bracer↔handgelenk`, `umhang↔cloak↔mantel`, `stiefel↔boots`, `handschuhe↔gloves`, `tasche↔bag`.
2. **Exact-/Alias-Lookup** gegen `alias_norm`, `display_{de,en}_norm`, `crafted_norm` → Score 1.0.
3. **FTS5**, OR-verknüpfte Prefix-Tokens (`wollstoff* tasche*`), `bm25(recipes_fts, 2.0, 1.5, 3.0, 2.5, 4.0)` — Alias und **Herstellungsprodukt** bekommen die höchsten Gewichte, weil Nutzer danach fragen.
4. **RapidFuzz** `process.extract(scorer=fuzz.WRatio)` über die **Top-200 FTS-Kandidaten** (nicht über alle — spart CPU auf dem Pi, erhöht Präzision). Fängt Tippfehler.
5. *(später, optional)* Lokale Embeddings via `fastembed` + `multilingual-e5-small`, Vektoren auf dem Pi vorberechnet. **Bewusst nicht über LM Studio** — das würde die Verfügbarkeitsannahme brechen, die nicht gilt.

**Ergebnis-Handling:**
- 1 Treffer, Score > 0.75 → direkt antworten
- 2–5 Treffer → „Meintest du …?"-`Select`. **Die Auswahl schreibt die Originalfrage in `alias_suggestions`; ab 3 übereinstimmenden Bestätigungen entsteht automatisch ein Alias.** Dieser Selbstlern-Loop ist langfristig wertvoller als jedes Modell-Upgrade — und bei einem noch unfertigen Spiel besonders, weil sich die Umgangssprache der Gilde erst bildet.
- 0 Treffer → Hinweis auf `/suche` und `/rezept melden`

**Aliase:** `aliases.de.yaml` handkuratiert (die lohnendsten ~100 Einträge, primär Verzauberungen mit Zahlenwerten). Dazu **generierte** Aliase beim Import: Name ohne Präfix, EN-Name ohne Präfix, Herstellungsprodukt-Name, Kompositum-Varianten („Wollstoff-Tasche" → „wollstofftasche", „wollstoff tasche").

> ⚠️ **Ehrliche Einschränkung:** Zahlenwerte wie „+35 Beweglichkeit" stehen typischerweise nicht im Rezeptnamen, sondern nur in der Zauberbeschreibung. Ob der Wowhead-Scrape diese Beschreibung mitliefert, ist **in M0 zu prüfen** — wenn ja, ist das Problem automatisch gelöst; wenn nein, müssen die Verzauberungs-Formeln von Hand aliasiert werden. Das ist die wichtigste offene Frage für genau deine erste Beispielfrage.

### SQL-Fallback (Intent = `unknown`)

Feature-Flag `config.ALLOW_LLM_SQL`, **Default `False`**, erst nach Release. Vier Sicherungen in `services/sqlguard.py`:

1. Separate Read-Only-Connection: `sqlite3.connect("file:...?mode=ro", uri=True)` + `PRAGMA query_only=ON` + `PRAGMA trusted_schema=OFF`
2. AST-Whitelist via `sqlglot.parse_one(sql, read="sqlite")`: genau ein `exp.Select`; kein `Insert/Update/Delete/Drop/Alter/Create/Pragma/Attach`; kein `;`; alle Tabellen in der Whitelist; kein `sqlite_*`
3. `LIMIT 50` im AST erzwingen
4. Harter Timeout: `conn.set_progress_handler(abort_cb, 1000)` → Abbruch nach 2 s, plus `asyncio.wait_for`

Generierte SQL im Embed-Footer anzeigen (Transparenz) und in `query_log` protokollieren.

### Ausgabe

`discord.Embed` mit **Monospace-Tabelle im Code-Block** in `description` — Embed-Fields rendern auf Mobile dreispaltig und brechen Tabellen. Limits: `description` ≤ 4096, Summe aller Embed-Teile ≤ 6000, Plain-Content ≤ 2000.

`utils/formatting.py::chunk_table(rows, headers, max_chars=3900) -> list[Embed]`, bei >1 Embed eine Paginierungs-View. Footer immer mit Modus und Katalogstand: `„12 Charaktere · Katalog 2026-11-04 · Basis-Suche"` bzw. `„· KI-Intent"`.

---

## Architektur & Projektstruktur

| Thema | Entscheidung | Begründung |
|---|---|---|
| **Ort** | Neuer Ordner `profession-helper-app/` | Folgt der Ein-Ordner-pro-Bot-Konvention. Anderer Deploy-Zyklus (RPi5 vs. GCE), andere Deps. Ein Absturz darf den Raid-Bot nicht mitreißen. |
| **Bot-Token** | Eigene Discord-Application | Braucht keine Channel-Manage-Rechte; eigene Präsenz („🟢 KI online" / „⚪ Basis-Modus"). Gemeinsame `secrets.json`, ein weiterer `DISCORD`-Eintrag. |
| **Cogs** | Ja, 6 Stück | ~22 Commands + Views + Autocomplete in einer Datei wird unwartbar. Bonus: LLM-Cog wird bei `ENABLE_LLM=false` gar nicht geladen. |
| **Alembic** | Nein | Ein Betreiber, ein Deployment. `services/migrations.py` mit `schema_version` und nummerierten `def m001(conn)` (~30 Zeilen). Tägliches Backup ersetzt die Migrations-Angst. |
| **Async DB** | Nein | Wenige hundert Rezepte/Chars, lokale SSD → Queries <1 ms. Synchrones DAO, konsequent via `await asyncio.to_thread(...)`. |
| **Tests** | Ja, 5 Dateien | `test_resolver.py` (~60 Paare *Frage → erwartetes Rezept*) ist der wichtigste Test im Projekt. Dazu `test_catalog_merge.py` (Provisorien-Merge!), `test_catalog.py`, `test_sqlguard.py`, `test_formatting.py`. |
| **Ruff** | Ja | `ruff.toml`, 5 Minuten. Kein CI nötig. |

```
profession-helper-app/
  pyproject.toml   uv.lock   ruff.toml
  bot.py                    # setup_hook, load_extension, on_ready, tree.sync
  config.py                 # Konstanten + ENV-Overrides
  cogs/      characters.py  professions.py  recipes.py  query.py  ask.py  admin.py
  services/  database.py  models.py  migrations.py  dao.py
             queries.py    # Intent -> parametrisierte SQL
             resolver.py   # Entity-Resolution
             catalog.py    # Import, Diff, Provisorien-Merge, FTS-Rebuild
             llm.py        # LmStudioClient + CircuitBreaker + Intent-Schema
             sqlguard.py
  utils/     logger.py  secrets.py  formatting.py  textnorm.py  http.py
  data/catalog/  current.json  snapshots/  aliases.de.yaml  overrides.yaml
  tools/     scrape_wowhead.py  build_catalog.py  catalog_sources.md
  tests/     test_resolver.py  test_catalog_merge.py  test_catalog.py
             test_sqlguard.py  test_formatting.py
  deploy/    profession-helper.service  backup.sh  backup.timer
```

### Wiederverwendung aus dem bestehenden Code

- [utils/logger.py](../group-helper-app/utils/logger.py) → **kopieren**, aber `LOG_DIR` aus ENV statt des hartkodierten `'logs/'` in [Zeile 14](../group-helper-app/utils/logger.py#L14) — sonst schreibt der systemd-Dienst ins falsche Verzeichnis.
- [utils/secrets.py](../group-helper-app/utils/secrets.py) → **kopieren und generalisieren**: eine `get_secret(section, match_field, match_value, value_field)`, spezifische Wrapper dünn darüber. Aktuell ist die Lookup-Logik dreifach dupliziert ([Zeilen 42–104](../group-helper-app/utils/secrets.py#L42-L104)).
- [services/database.py](../group-helper-app/services/database.py) → **neu schreiben, nicht kopieren.** Zwei Bugs nicht erben: `DB_PATH = Path("data/...")` ist [relativ zum CWD](../group-helper-app/services/database.py#L7) (bricht unter systemd still und legt eine leere DB am falschen Ort an), und `sqlalchemy.ext.declarative.declarative_base` in [Zeile 2](../group-helper-app/services/database.py#L2) ist in 2.0 deprecated. Neu: `PROFESSION_DB_PATH` aus ENV, `class Base(DeclarativeBase)`. Das Pooling-Setup ([Zeilen 10–17](../group-helper-app/services/database.py#L10-L17)) wird übernommen.
- [services/scheduler.py](../group-helper-app/services/scheduler.py) → Muster (`SessionLocal()` + try/commit/rollback/close) ist okay, aber der Aufruf aus async-Handlern blockiert den Event-Loop. Hier konsequent `await asyncio.to_thread(dao.fn, ...)`.
- [services/raid_helper.py](../group-helper-app/services/raid_helper.py) → **nicht als Vorlage nehmen.** Erstellt pro Call eine neue `ClientSession` und gibt die Response außerhalb des `async with` zurück. Neu: Singleton-Session in `utils/http.py`, im `setup_hook` erzeugt — die braucht der Scraper ohnehin mit Rate-Limit und Retry.

---

## Betrieb auf dem RPi5

**OS:** Raspberry Pi OS Bookworm **64-bit (arm64)** — Pflicht, sonst keine manylinux-aarch64-Wheels.

**Python:** `uv python install 3.13`, `requires-python = ">=3.13"`. 3.14 würde vermutlich laufen, aber uv ist auf aarch64 nur Tier-2 und die cp314-Wheel-Abdeckung ist dünn. 3.13 ist risikofrei ohne Funktionsverlust. *(Bewusste Abweichung vom bestehenden `group-helper-app` mit `>=3.14`.)*

**FTS5:** python-build-standalone baut SQLite mit `-DSQLITE_ENABLE_FTS5`. Trotzdem beim Start `PRAGMA compile_options` prüfen und bei Fehlen auf reines RapidFuzz degradieren (`resolver.FTS_AVAILABLE`), damit das Projekt nicht an dieser Annahme hängt.

**systemd** (`deploy/profession-helper.service`) — **alle Pfade absolut aus ENV**:

```ini
[Service]
Type=simple
User=guildbot
WorkingDirectory=/opt/profession-helper-app
Environment=SECRETS_PATH=/etc/profession-helper/secrets.json
Environment=PROFESSION_DB_PATH=/var/lib/profession-helper/profession_helper.db
Environment=CATALOG_DIR=/var/lib/profession-helper/catalog
Environment=LOG_DIR=/var/log/profession-helper
Environment=LMSTUDIO_BASE_URL=http://192.168.1.50:1234/v1
ExecStart=/home/guildbot/.local/bin/uv run --frozen python bot.py
Restart=always
RestartSec=10
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=/var/lib/profession-helper /var/log/profession-helper
```

**Backup:** Beim Start `PRAGMA journal_mode=WAL` + `synchronous=NORMAL`. `backup.timer` täglich 04:00 → `sqlite3 "$DB" ".backup '/var/backups/profession-helper/ph_$(date +%F).db'"` (konsistent auch bei laufendem Bot), dann `gzip`. Retention 14 täglich + 8 wöchentlich, plus `rclone`/`scp` auf NAS oder den LM-Studio-PC. Zielverzeichnis `/var/backups/profession-helper/`.
Zusätzlich infrastrukturfrei: `/admin export` postet `characters` + `character_professions` + `character_recipes` als JSON-Attachment in einen privaten Channel. **Nur diese drei Tabellen sind nicht reproduzierbar** — der Katalog lässt sich jederzeit neu scrapen.

**Netzwerk RPi → LM Studio:** In LM Studio „Serve on Local Network" aktivieren (sonst bindet der Server nur auf `127.0.0.1`), Windows-Firewall Port 1234 im **privaten** Profil freigeben, DHCP-Reservierung für die PC-IP. LM Studio hat keine Auth — Absicherung rein über das LAN.

**LLM nicht erreichbar** (`services/llm.py`):
- `ClientTimeout(total=8, connect=1.5, sock_read=8)` auf der Singleton-Session
- `CircuitBreaker`: 3 Fehler in Folge → `OPEN` für 120 s. Im OPEN-Zustand wird gar nicht erst verbunden → der Nutzer wartet **null** Sekunden.
- `@tasks.loop(minutes=2)` Health-Poll auf `GET {base}/models` → steuert `bot.change_presence`.
- **Kaltstart-Falle:** Der erste Call nach LM-Studio-Start lädt das Modell (10–60 s). Deshalb HALF_OPEN-Probe mit 90 s Timeout *aus dem Health-Task heraus*; echte Nutzer-Calls bleiben bei 8 s.
- Jede degradierte Antwort sagt es im Footer: „ℹ️ KI-Assistent offline — Basis-Suche verwendet."

---

## Meilensteine (Stichtag: Release 4.11.2026)

**M0 — Scraper-Spike** *(2–3 Tage, kein Discord-Code)* ⚠️ **größtes Risiko, zuerst**
Prüfen, ob die Wowhead-Listings das `Listview`-Datenarray liefern; ob Quelle (Trainer/Drop/Quest) und **Herstellungsprodukt** enthalten sind; ob die Zauberbeschreibung mit Zahlenwerten („+35 Beweglichkeit") erreichbar ist; ob `/forever/de/` deutsche Namen liefert; und was die Kategorie „Books" tatsächlich enthält (falls dort Rezepte primärer Berufe stecken, muss sie mit in den Scope). `scrape_wowhead.py` + `build_catalog.py`, Rate-Limit 1 req/s, Ergebnis als Snapshot-JSON.
**Abnahme:** 20 Rezepte stichprobenartig gegen die Wowhead-Website prüfen — Beruf, Name, Quelle, Herstellungsprodukt korrekt? **Erst dann geht M1 los.** Fällt der Spike negativ aus, ist der Addon-Weg zu bewerten (siehe unten) — lieber jetzt als im Oktober.

**M1 — Erfassung + deterministische Abfrage, ohne LLM** *(bis ~10.10.)* → *liefert ~80 % des Nutzens*
Projektgerüst, DB/Models/Migrations, Katalog-Import mit Diff; Cogs `characters`, `professions`, `recipes` (Weg A + `/rezept melden`); Cog `query` mit `/wer beruf`, `/wer kann`, `/suche`; Resolver-Stufen 1–2; systemd + Backup-Timer auf dem Pi.
→ **„Wer ist Verzauberer?" und „Wer kann Wollstofftaschen herstellen?" sind ab hier beantwortbar.**

**M2 — Release-Readiness** *(bis ~31.10.)* — **nicht optional**
`RecipeWizardView` (Massenerfassung fürs Onboarding), Modal-Suchfilter, `/rezept meine`, `/rezept entfernen`, Provisorien-Auto-Merge + Admin-Review-Queue, `/admin katalog-update` + wöchentlicher Job + Diff-Report, `overrides.yaml`.
→ Stand 31.10. muss der Bot einen Gilden-Ansturm in einer Woche verkraften.

**🚩 4.11. — Release-Tag**
Voll-Scrape des finalen Katalogs, Snapshot einchecken, Plausibilitätscheck, Gilde onboarden. Danach **täglich** `/admin katalog-update`, weil Wowhead in den ersten Wochen am schnellsten nachfüllt.

**M3 — Resolver-Ausbau (weiterhin LLM-frei)** *(November)*
FTS5, RapidFuzz-Kaskade, Slot-Synonym-Map, generierte Aliase, `aliases.de.yaml` handkuratieren, „Meintest du …?"-Select mit Selbstlern-Loop, `test_resolver.py` gefüttert aus dem `query_log` der ersten Release-Wochen — **echte Gildenfragen statt erfundener Testfälle.**

**M4 — LLM-Intent-Layer** *(Dezember)*
`services/llm.py` (Structured Output, Circuit Breaker, Health-Task), Cog `ask` mit `/frage` und optionalem `on_message` in einem konfigurierten Channel. Deutscher System-Prompt + Few-Shots.
**Gate vor Rollout:** Eval-Set mit 50 echten Gildenfragen aus `query_log`, Intent-Accuracy messen, 2–3 Modelle vergleichen.

**M5 — Optional, nur bei Bedarf**
`sqlguard.py` + LLM-SQL hinter Feature-Flag; lokale Embeddings als Resolver-Stufe 5. **Nur bauen, wenn `query_log` zeigt, dass `intent=unknown` wirklich häufig ist.**

---

## Verifikation

**M0 — Scrape:**
```bash
cd profession-helper-app
uv run python tools/scrape_wowhead.py --profession enchanting --out /tmp/raw.json
uv run python tools/build_catalog.py --in /tmp/raw.json --out data/catalog/snapshots/probe.json
uv run python -c "import json;d=json.load(open('data/catalog/snapshots/probe.json'));r=d['recipes'];\
print(len(r), sum(1 for x in r if x.get('crafted_name_en')), sum(1 for x in r if x.get('name_de')))"
```
Erwartung: plausible Anzahl, **Herstellungsprodukt bei der großen Mehrheit gefüllt** (sonst scheitert die Wollstofftaschen-Frage), deutscher Name bei mindestens einem Teil. Dann 20 Stichproben gegen die Website.

**M1 — echter Discord-Test in der DEBUG-Guild:**
1. `DEBUG=True` + `DEBUG_GUILD_ID` → guild-scoped Sync ist sofort sichtbar (globaler Sync braucht bis zu 1 h).
2. `/char anlegen` → `/beruf setzen … skill:300` → `/rezept hinzufuegen`: beim Tippen von „woll" müssen Wollstoff-Rezepte erscheinen — **auch beim Tippen des Produktnamens, nicht nur des Rezeptnamens.**
3. `/wer beruf` und `/wer kann` liefern denselben Charakter.
4. `/rezept melden name:"Irgendein Beta-Rezept"` → taucht in `/wer kann` mit `*`-Markierung auf.
5. Bot stoppen, DB prüfen, neu starten → Daten noch da.

**M2 — Provisorien-Merge (der heikelste Automatismus):**
```bash
uv run pytest tests/test_catalog_merge.py -v
```
Deckt ab: exakter Treffer merged, knapper Treffer landet in der Review-Queue, Nicht-Treffer bleibt provisorisch, `character_recipes` verliert **nie** eine Zeile. Dann manuell: Rezept melden → Katalog mit passendem Eintrag importieren → `/wer kann` zeigt es ohne `*`, der Melder bekommt eine DM.

**Automatisiert:**
```bash
uv run pytest tests/ -v
uv run ruff check . && uv run ruff format --check .
```

**M4 — LLM-Ausfall (wichtigster Test des Features):**
```bash
curl http://<PC-IP>:1234/v1/models        # vom RPi aus, nicht vom PC!
```
Dann **LM Studio bewusst beenden** und `/frage` erneut stellen: Es muss innerhalb von ~1,5 s eine Basis-Antwort mit Offline-Footer kommen — kein Timeout, kein Fehler.

---

## Risiken

1. **M0-Spike kann scheitern.** Wowhead könnte die Daten nicht im erwarteten Format liefern, Quellenangaben könnten fehlen, oder Scraping wird blockiert. Deshalb steht M0 ganz vorne — ein negatives Ergebnis im September ist verkraftbar, im Oktober nicht.
2. **Wowhead-ToS.** Grauzone für ein privates Tool. Mitigation über Rate-Limit, Caching und Nicht-Weiterverbreitung; Ersatzquelle siehe unten.
3. **„+35 Beweglichkeit"-Fragenklasse** hängt davon ab, ob der Scrape Zauberbeschreibungen liefert. Falls nicht: manuelle Aliase, ~1–2 h.
4. **Beta-Daten ≠ Release-Daten.** Bewusst akzeptiert: die Gilde erfasst erst ab dem 4.11. Beta-Daten dienen nur dem Testen der Maschinerie.
5. **Auto-Merge könnte falsch zuordnen** und damit stillschweigend Falschdaten erzeugen. Mitigation: hohe Schwelle (0.88), Review-Queue für alles darunter, `character_recipes` wird nie gelöscht, `test_catalog_merge.py` als Pflichttest.
6. **Release-Ansturm.** Onboarding-Wizard muss am 4.11. stehen, sonst versandet die Adoption in der Woche mit dem größten Interesse.
7. **Größtes nicht-technisches Risiko: Datenpflege-Disziplin.** Ein perfekter Katalog ohne gepflegte Charaktere ist wertlos.

---

## Offene Optionen (bewusst nicht jetzt entschieden)

**In-Game-Addon-Export.** Ein Addon, das die Berufsfenster in einen Text-String dumpt, den man in Discord pastet. Vorteile in genau dieser Situation erheblich: der Client kennt die Rezepte des Spielers **autoritativ und aktuell**, auch die, die Wowhead noch nicht hat — und Erfassung dauert Sekunden statt Minuten. Kosten: ein Addon schreiben und in der Gilde verteilen.

Bewusst nicht Teil des Plans, weil Katalog + Auswahlmenüs entschieden sind und ohne Zusatzsoftware auskommen. **Aber zwei Auslöser sollten die Entscheidung neu aufwerfen:** wenn der M0-Spike scheitert, oder wenn nach dem Release auffällig viele `/rezept melden`-Einträge auflaufen — dann ist Wowhead als alleinige Quelle zu langsam für das Tempo des Spiels.
