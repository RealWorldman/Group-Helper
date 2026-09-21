# Wowhead als Katalogquelle — Endpoints, Felder, Codes

Referenz für alle, die am Scraper oder am Katalog-Import arbeiten.
Alles hier ist aus echten Antworten belegt, nicht aus Dokumentation abgeleitet — Wowhead
dokumentiert diese Strukturen nirgends. Jede Aussage trägt deshalb einen Status:

| Status | Bedeutung |
|---|---|
| ✅ belegt | in den Daten nachgewiesen, Gegenprobe gemacht |
| 🟡 vermutet | plausibel, aber nicht gegengeprüft |
| ❔ offen | noch nicht untersucht |

**Datenstand:** 21.09.2026, Beruf Schneiderei (`skill=197`), 477 Einträge, Beta-Phase.
**Rohdaten:** `data/probe/tailoring.json` (EN) und `data/probe/tailoring.de.json` (DE).

---

## 1. Endpoints

### Was funktioniert

| URL | Liefert | Status |
|---|---|---|
| `/forever/spells/professions/<beruf>` | alle Berufszauber, pro Beruf gefiltert, nicht gekappt | ✅ |
| `/forever/de/spells/professions/<beruf>` | dasselbe auf Deutsch, identische IDs | ✅ |

Das Datenarray steht als `var listviewspells = [...]` direkt im HTML. **Ein Request pro Beruf
und Sprache** — kein Paging, kein Request pro Item.

### Was nicht funktioniert

| URL | Problem | Status |
|---|---|---|
| `/forever/items/recipes` | bei 1.000 Einträgen gekappt (`note: "2,657 items found (1,000 displayed)"`) | ✅ |
| `/forever/items/recipes/tailoring-patterns` | **Kategorie-Slug filtert nicht** — liefert dieselbe ungefilterte Liste | ✅ |
| `/forever/de/skill=197/schneiderei` | bettet die Daten anders ein (`data: [...]` innerhalb `new Listview({...})`, kein `var listviewspells`) | ✅ |

> ⚠️ **Alles ab `#` in einer Wowhead-URL ist ein Fragment** und erreicht den Server nie.
> `#recipes;source=Drop` filtert clientseitig im bereits geladenen Array. Für uns heißt das:
> Wir bekommen ohnehin den vollen Datensatz und filtern selbst über das Feld `source`.

### Reproduktion

```bash
cd profession-helper-app
uv run python tools/probe_listing.py --profession tailoring --out data/probe/tailoring.json
uv run python tools/probe_listing.py --profession tailoring --locale de --out data/probe/tailoring.de.json
```

Der Join beider Sprachen läuft über `id` (= `spell_id`) und ist verlustfrei: gleiche 477 IDs
in beiden Sprachen, keine Waisen in eine Richtung.

### Rate-Limit und Umgang

- **max. 1 Request/Sekunde**, auch wenn es nur eine Handvoll Requests sind
- `User-Agent` mit Projektname und Kontaktadresse — keine Browser-Tarnung
- Roh-HTML lokal cachen, nicht für jeden Testlauf neu ziehen
- **keine öffentliche Weiterverbreitung des Datensatzes** (siehe Risiko 2 im Plan)

---

## 2. Feldreferenz `listviewspells`

Abdeckung gemessen an den 477 Schneiderei-Einträgen.

| Feld | Typ | Abdeckung | Bedeutung |
|---|---|---:|---|
| `id` | int | 100 % | **spell_id** — Primärschlüssel, stabil über Sprachen hinweg |
| `name` | string | 100 % | **Name des hergestellten Gegenstands**, lokalisiert |
| `displayName` | string | 100 % | bisher immer identisch zu `name` |
| `learnedat` | int | 100 % | benötigter Berufs-Skill (`9999` = Berufsrang, kein Rezept) |
| `skill` | int[] | 100 % | Skill-Line-ID des Berufs (Schneiderei = `197`) |
| `cat` | int | 100 % | Berufs-Kategorie (Schneiderei = `11`) |
| `quality` | int | 100 % | Item-Qualität; **`-1` = kein verknüpftes Item**, siehe Abschnitt 4 |
| `nskillup`, `level`, `schools`, `popularity` | int | 100 % | für uns ohne Bedeutung |
| `reagents` | [[int,int]] | 98,3 % | `[[item_id, menge], ...]` |
| `colors` | int[4] | 97,1 % | Skill-Farbstufen `[orange, gelb, grün, grau]` |
| `creates` | [int,int,int] | 83,2 % | `[item_id, min_menge, max_menge]` des Produkts |
| `source` | int[] | 52,8 % | Bezugsquellen, siehe Abschnitt 3 |
| `trainingcost` | int | 18,0 % | Kosten beim Lehrer in Kupfer |
| `rank` | string | 2,5 % | nur bei Berufsrang-Einträgen (`"Lehrling"`, `"Geselle"`, …) |
| `races`, `reqrace` | int[] | 0,4 % | Volks-Beschränkung |

### Beispiel-Eintrag

```json
{
  "id": 2385,
  "name": "Braune Leinenweste",
  "creates": [2568, 1, 1],
  "learnedat": 10,
  "colors": [10, 45, 57, 70],
  "reagents": [[2996, 1], [2320, 1]],
  "source": [6],
  "trainingcost": 50,
  "quality": 1,
  "cat": 11,
  "skill": [197]
}
```

### Parsing-Fallen

Das Array ist **kein gültiges JSON**:

1. **Gemischte Schlüssel** — `"quality":1` steht neben `popularity:10` und `firstseenpatch: 0`.
   Unquoted Schlüssel müssen vor `json.loads` nachgerüstet werden.
2. **Doppelte Schlüssel** — `quality` kommt in manchen Einträgen zweimal vor, quoted und
   unquoted. `json.loads` behält den letzten; für `quality` ist das unkritisch.
3. **Die Reparatur darf nur außerhalb von Strings laufen.** Ein Item namens
   `Ring, Gold: Klein` sieht sonst aus wie ein unquoted Schlüssel und wird zerschnitten.
4. **Klammern und escapte Anführungszeichen in Namen** (`Trank [gross]`,
   `Khadgar\"s Unlocking`) brechen jede naive Regex — deshalb zählt
   `extract_listview()` die Schachtelungstiefe zeichenweise und überspringt Stringinhalt.

Implementiert und gegen alle vier Fälle geprüft in [probe_listing.py](probe_listing.py).

---

## 3. Die Codes im Feld `source`

Ein Eintrag kann mehrere Quellen haben: `Rote Leinenrobe` hat `[2, 16, 21]`.

| Code | Anzahl | davon mit `trainingcost` | Bedeutung | Status |
|---:|---:|---:|---|---|
| `2` | 102 | 0 | **Drop** | ✅ belegt |
| `6` | 86 | **86** | **Lehrer** | ✅ belegt |
| `5` | 60 | 0 | **Händler** | ✅ belegt |
| `16` | 19 | 0 | **Geangelt** | ✅ belegt |
| `4` | 6 | 0 | **Quest** | ✅ belegt |
| `21` | 6 | 0 | **Aus Taschendiebstahl** | ✅ belegt |

Die Zuordnung ist vollständig — es gibt in den Schneiderei-Daten keinen weiteren Code.
Dass ausgerechnet *Angeln* und *Taschendiebstahl* als Quellen auftauchen, ist kein Fehler:
Das Rezept-**Item** wird so erlangt (aus erangelten Behältern bzw. von bestohlenen
Humanoiden), nicht der Zauber selbst.

### Warum Code 6 = Lehrer belegt ist

Die Korrelation mit `trainingcost` ist in **beide** Richtungen perfekt:

- alle 86 Einträge mit Code `6` haben ein `trainingcost`
- kein einziger Eintrag hat `trainingcost` ohne Code `6`

Damit steht der Trainer-Filter (Entscheidung 3 im Plan) auf belastbarem Fundament.

### Warum der Trainer-Filter trotzdem weich bleiben muss

**225 der 477 Einträge (47 %) haben überhaupt kein `source`-Feld.** Wir können also sagen
„das ist sicher ein Lehrer-Rezept", aber nie „das ist sicher keins". Genau deshalb blendet
der Import Trainer-Rezepte nur aus, statt sie wegzulassen — ein Fehlurteil der Quelle darf
keine Daten kosten.

Die Lücke ist nicht gleichmäßig verteilt, sondern fast vollständig neues Forever-Material
(469 echte Rezepte, Berufsränge herausgerechnet):

| | n | ohne `source` | davon Lehrer (Code 6) |
|---|---:|---:|---:|
| Classic (`id < 400k`) | 228 | 12 (**5,3 %**) | 77 |
| Forever (`id ≥ 400k`) | 241 | 209 (**86,7 %**) | 5 |

Drei Schlüsse daraus:

1. **Für Classic-Rezepte ist die Quellenangabe praktisch vollständig** — dort funktioniert
   der Trainer-Filter heute schon zuverlässig.
2. **Für Forever-Rezepte funktioniert er derzeit fast gar nicht.** Die 5 Lehrer-Treffer unter
   241 neuen Rezepten sind mit hoher Wahrscheinlichkeit ein Artefakt der fehlenden Daten,
   keine Design-Entscheidung von Forever. Aus dieser Zahl darf **nichts** abgeleitet werden.
3. Beides zusammen ist das stärkste Argument für den **täglichen** `/admin katalog-update`
   nach dem Release: Genau hier füllt Wowheads Crowdsourcing in den ersten Wochen nach, und
   genau hier braucht `overrides.yaml` am ehesten Handarbeit.

### Wie die Codes belegt wurden

Die Seite `/forever/de/skill=197/schneiderei#recipes;source=<Quelle>` filtert clientseitig
und zeigt die Trefferzahl über der Tabelle an. Für jede Quelle im Dropdown wurde diese Zahl
mit der Häufigkeit des Codes in unseren Daten verglichen — alle sechs stimmen exakt überein
(Abgleich am 21.09.2026).

Dasselbe Verfahren gilt für jeden Code, der bei den übrigen Berufen neu auftaucht:
Code zählen, im Dropdown gegenprüfen, hier eintragen. **Ein unbekannter Code darf nicht
stillschweigend als „kein Lehrer-Rezept" durchrutschen** — der Import soll ihn im
Diff-Report melden.

---

## 4. Lücken in den Quelldaten

### `creates` fehlt bei 80 Einträgen (16,8 %)

Davon sind **8 gar keine Rezepte**, sondern die Berufsränge selbst (`name: "Schneiderei"`,
`rank: "Lehrling"/"Geselle"/"Experte"/"Fachmann"`, `learnedat` 50/125/200/9999).
→ **Der Import muss diese herausfiltern.**

Die übrigen **72 sind echte Rezepte, denen nur die Item-Verknüpfung fehlt.** Der Grund ist
das Alter des Zaubers:

| | id-Bereich | davon `id ≥ 400.000` |
|---|---|---|
| mit `creates` | 2.385 – 1.306.545 | 169 / 397 (43 %) |
| ohne `creates` | 3.908 – 1.292.980 | **76 / 80 (95 %)** |

IDs ab ~400.000 sind neue Forever-Zauber. Wowheads Crowdsourcing hat die Item-Verknüpfung
dort schlicht noch nicht nachgetragen. Das ist die „systematisch unvollständige" Quelle aus
dem Plan — kein Parsing-Fehler.

**Wichtig: Der Produktname ist trotzdem vorhanden.** Alle 72 haben ein gefülltes `name`-Feld
mit dem Produktnamen (`Crimson Silk Robe`, `Extraplanar Spidersilk Boots`). Für die Frage
„Wer kann mir X machen?" reicht das — die `item_id` braucht man erst für Icon und
Wowhead-Link.

### `quality == -1` ist der Marker dafür

Exakt die 80 Einträge ohne `creates` haben `quality == -1`, und kein Eintrag **mit**
`creates` hat `-1`. ✅ belegt, null Fehltreffer in beide Richtungen.

Der Import kann diese Rezepte damit zuverlässig als „Produkt bekannt, Item-Link fehlt noch"
kennzeichnen und beim nächsten Katalog-Update automatisch nachziehen.

### Mehrfach belegte Namen

Mehrfach belegte Namen: **20 auf Englisch, 19 auf Deutsch.** Acht davon sind die
Berufsrang-Einträge; der Rest sind Paare aus Classic-Version und überarbeiteter
Forever-Version:

```
  18455  creates=[14156, 1, 1]  Bodenlose Tasche / Bottomless Bag   (Classic)
 463972  creates=None           Bodenlose Tasche / Bottomless Bag   (Forever)
```

Kein Problem für den Import (die `spell_id` bleibt eindeutig), aber der Resolver muss in M3
mit Mehrdeutigkeit umgehen können.

> Dass die Zahl zwischen DE und EN abweicht, ist kein Zählfehler: Zwei Rezepte, die auf
> Englisch denselben Namen tragen, können auf Deutsch unterschiedlich heißen — und
> umgekehrt. **Die Mehrdeutigkeit ist also sprachabhängig.** Der Resolver darf daraus nicht
> ableiten, dass ein Name eindeutig ist, nur weil er es in einer der beiden Sprachen ist.

---

## 5. Lokalisierung

| | Ergebnis | Status |
|---|---|---|
| deutsche Namen vorhanden | **477 / 477** | ✅ |
| davon Classic (`id < 400k`) | 232 / 232 | ✅ |
| davon Forever (`id ≥ 400k`) | 245 / 245 | ✅ |
| Join über `id` verlustfrei | 0 Waisen in beide Richtungen | ✅ |

```
  2385  Brown Linen Vest        -> Braune Leinenweste
  2386  Linen Boots             -> Leinenstiefel
  2395  Barbaric Linen Vest     -> Barbarische Leinenweste
```

Die Übersetzung ist damit **weiter, als der Plan ursprünglich annahm**. Der EN-Fallback
bleibt als Sicherungsnetz, ist aber nicht der Normalfall. Beide Namen werden gespeichert und
indiziert — siehe *Zweisprachigkeit* im [Plan](../PLAN.md).

> Konsolen-Hinweis: Unter Windows zerlegt die Standard-Codepage Umlaute in der Ausgabe.
> Die Daten selbst sind UTF-8 (`ß` = `0xC3 0x9F`, in der Datei verifiziert).
> Mit `PYTHONIOENCODING=utf-8` stimmt auch die Anzeige.

---

## 6. Noch offen

| Frage | Warum sie zählt |
|---|---|
| Gilt all das auch für die anderen sechs Berufe? | Bisher ist nur Schneiderei untersucht |
| Liefert der Scrape die **Zauberbeschreibung** mit Zahlenwerten? | Entscheidet über die Fragenklasse „+35 Beweglichkeit" (Risiko 3 im Plan) |
| Was enthält die Kategorie „Books"? | Falls dort Rezepte primärer Berufe stecken, muss sie in den Scope |
| Slugs der übrigen Berufe | `tailoring` ist belegt, die anderen sechs sind geraten |
| Tauchen bei anderen Berufen weitere `source`-Codes auf? | Verfahren siehe Abschnitt 3 |
