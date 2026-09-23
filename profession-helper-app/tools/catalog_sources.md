# Wowhead als Katalogquelle — Endpoints, Felder, Codes

Referenz für alle, die am Scraper oder am Katalog-Import arbeiten.
Alles hier ist aus echten Antworten belegt, nicht aus Dokumentation abgeleitet — Wowhead
dokumentiert diese Strukturen nirgends. Jede Aussage trägt deshalb einen Status:

| Status | Bedeutung |
|---|---|
| ✅ belegt | in den Daten nachgewiesen, Gegenprobe gemacht |
| 🟡 vermutet | plausibel, aber nicht gegengeprüft |
| ❔ offen | noch nicht untersucht |

**Datenstand:** 23.09.2026, Beta-Phase. Alle sieben Berufe geladen (Abschnitt 1a); die
`source`-Codes (Abschnitt 3) sind für alle ausgewertet. Die übrige Tiefenanalyse
(Abschnitte 2, 4, 5) stützt sich bisher nur auf Schneiderei (`skill=197`, 477 Einträge).
**Rohdaten:** `data/probe/<slug>.json` (EN) und `data/probe/<slug>.de.json` (DE),
Roh-HTML daneben als `<slug>[.de].html` (gitignored).

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
# alle sieben Berufe x EN/DE, 1 req/s, HTML-Cache in data/probe/ (14 Requests beim ersten Lauf)
uv run python tools/probe_all.py
# einzelner Beruf, ohne Cache
uv run python tools/probe_listing.py --profession tailoring --locale de --out data/probe/tailoring.de.json
```

`probe_all.py` holt nur Seiten, deren HTML noch nicht im Cache liegt (`--refetch` erzwingt
alles neu). Regressionsprobe am 21.09.2026: Die neu geholten Seiten für Schneiderei (EN/DE)
und Verzauberkunst (DE) ergaben **byteweise identisches JSON** zu den vorher eingecheckten
Dateien — Parser und Quelle stabil.

Der Join beider Sprachen läuft über `id` (= `spell_id`) und ist für Schneiderei verlustfrei: gleiche 477 IDs
in beiden Sprachen, keine Waisen in eine Richtung.

### Rate-Limit und Umgang

- **max. 1 Request/Sekunde**, auch wenn es nur eine Handvoll Requests sind
- `User-Agent` mit Projektname und Kontaktadresse — keine Browser-Tarnung
- Roh-HTML lokal cachen, nicht für jeden Testlauf neu ziehen
- **keine öffentliche Weiterverbreitung des Datensatzes** (siehe Risiko 2 im Plan)

## 1a. Berufe, Slugs, Skill-IDs

Alle sieben Slugs am 21.09.2026 per `probe_all.py` geprüft — kein Fehlschlag. ✅ belegt

| Beruf | Slug | `skill` | Einträge EN | Einträge DE | `source`-Codes |
|---|---|---:|---:|---:|---|
| Alchemie | `alchemy` | 171 | 202 | 202 | 1, 2, 4, 5, 6, 16, 21 |
| Schmiedekunst | `blacksmithing` | 164 | 515 | 515 | 1, 2, 4, 5, 6, 16, 21 |
| Verzauberkunst | `enchanting` | 333 | 270 | 270 | 2, 5, 6, 16, 21 |
| Ingenieurskunst | `engineering` | 202 | 284 | 284 | 2, 4, 5, 6, 16, 21 |
| Lederverarbeitung | `leatherworking` | 165 | 613 | 613 | 2, 4, 5, 6, 16, 21 |
| Bergbau | `mining` | 186 | 29 | 29 | 6 |
| Schneiderei | `tailoring` | 197 | 477 | 477 | 2, 4, 5, 6, 16, 21 |

- **EN und DE haben bei jedem Beruf gleich viele Einträge.** Dass der Join über `id` auch
  überall verlustfrei ist und alles übersetzt ist, ist damit 🟡 vermutet — gemessen
  (`locale_join.py`) ist es bisher nur für Schneiderei.
- **Berufsübergreifende Rezepte:** Lederverarbeitung *und* Schneiderei enthalten Einträge mit
  `skill: [165, 197]`. Ein solcher Zauber steht in **beiden** Listings. → Der Import muss
  über `spell_id` deduplizieren und `skill` als Liste speichern. Wie viele Einträge das
  betrifft und ob es weitere Kombinationen gibt: ❔ offen.
- **Bergbau** hat nur 29 Einträge, alle mit Quelle `6` (Lehrer) — plausibel für Verhütten.

---

## 2. Feldreferenz `listviewspells`

Abdeckung gemessen an den 477 Schneiderei-Einträgen.

| Feld | Typ | Abdeckung | Bedeutung |
|---|---|---:|---|
| `id` | int | 100 % | **spell_id** — Primärschlüssel, stabil über Sprachen hinweg |
| `name` | string | 100 % | **Name des hergestellten Gegenstands**, lokalisiert |
| `displayName` | string | 100 % | bisher immer identisch zu `name` |
| `learnedat` | int | 100 % | benötigter Berufs-Skill (`9999` = Berufsrang, kein Rezept) |
| `skill` | int[] | 100 % | Skill-Line-ID(s) des Berufs (Schneiderei = `197`) — **kann mehrere enthalten**, z. B. `[165, 197]`; IDs aller Berufe in Abschnitt 1a |
| `cat` | int | 100 % | Zauber-Kategorie „Berufe" — **bei allen sieben Berufen `11`**, taugt nicht zur Berufszuordnung ✅ |
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
| `1` | 2 | 0 | **Hergestellt** | ✅ belegt |
| `2` | 102 | 0 | **Drop** | ✅ belegt |
| `6` | 86 | **86** | **Lehrer** | ✅ belegt |
| `5` | 60 | 0 | **Händler** | ✅ belegt |
| `16` | 19 | 0 | **Geangelt** | ✅ belegt |
| `4` | 6 | 0 | **Quest** | ✅ belegt |
| `21` | 6 | 0 | **Aus Taschendiebstahl** | ✅ belegt |
| `1` | 2 | 0 | **Hergestellt** — nur bei Alchemie und Schmiedekunst, je 1 Eintrag | ✅ belegt (schmal) |

Die Anzahlen der Codes `2`–`21` gelten für Schneiderei; die Zahlen pro Beruf stehen weiter
unten. Über alle sieben Berufe tauchen **genau diese sieben Codes** auf, kein weiterer.

> ⚠️ **Code `1` ist belegt, aber auf schmaler Basis.** Die Bedeutung „Hergestellt" wurde am
> 23.09.2026 im Wowhead-WebUI gegengeprüft. Es gibt jedoch **im gesamten Datenbestand nur
> zwei Einträge damit**: `Goblin-Raketentreibstoff` (Alchemie) und `Veredelter
> Mithrilzylinder` (Schmiedekunst), beide ohne `trainingcost`. Bei einer Trefferzahl von 1
> kann ein Dropdown-Abgleich zufällig stimmen — auf diese Zuordnung darf später kein
> Gewicht gelegt werden, das über „zwei Einzelfälle" hinausgeht.

Dass ausgerechnet *Angeln* und *Taschendiebstahl* als Quellen auftauchen, ist kein Fehler:
Das Rezept-**Item** wird so erlangt (aus erangelten Behältern bzw. von bestohlenen
Humanoiden), nicht der Zauber selbst.

### Warum Code 6 = Lehrer belegt ist

Die Korrelation mit `trainingcost` ist in **beide** Richtungen perfekt — und zwar bei
**allen sieben Berufen**, nicht nur bei Schneiderei (`source_codes.py`, 23.09.2026):

| Beruf | Einträge | Code `6` | davon mit `trainingcost` | `trainingcost` ohne Code `6` | ohne `source` |
|---|---:|---:|---:|---:|---:|
| Alchemie | 202 | 35 | 35 | **0** | 92 (45,5 %) |
| Schmiedekunst | 515 | 81 | 81 | **0** | 261 (50,7 %) |
| Verzauberkunst | 270 | 66 | 66 | **0** | 109 (40,4 %) |
| Ingenieurskunst | 284 | 78 | 78 | **0** | 125 (44,0 %) |
| Lederverarbeitung | 613 | 74 | 74 | **0** | 349 (56,9 %) |
| Bergbau | 29 | 12 | 12 | **0** | 17 (58,6 %) |
| Schneiderei | 477 | 86 | 86 | **0** | 225 (47,2 %) |

Damit steht der Trainer-Filter (Entscheidung 3 im Plan) berufsübergreifend auf
belastbarem Fundament.

> Ein Rezept kann mehrere Quellen haben. Bei Alchemie tragen deshalb auch Einträge mit
> Code `2` (Drop) oder `5` (Händler) ein `trainingcost` — sie haben zusätzlich Code `6`.
> Das ist kein Widerspruch zur Spalte „`trainingcost` ohne Code `6`".

### Warum der Trainer-Filter trotzdem weich bleiben muss

**Die `source`-Lücke liegt bei jedem Beruf zwischen 40,4 % und 58,6 %** (Spalte ganz rechts
oben) — bei Schneiderei sind es 225 der 477 Einträge. Wir können also sagen
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

## 6. Der zweite Datenblock: `WH.Gatherer.addData`

**Jede Listing-Seite enthält neben `var listviewspells` einen zweiten Datenblock**, der beim
ersten Spike übersehen wurde. Er kostet keinen zusätzlichen Request. ✅ belegt (23.09.2026)

```js
WH.Gatherer.addData(3, 16, {"6217": {...}, ...})   // Items,  Schlüssel = item_id
WH.Gatherer.addData(6, 16, {"7421": {...}, ...})   // Zauber, Schlüssel = spell_id
```

Anders als `listviewspells` ist dieser Block **gültiges JSON** — alle Schlüssel sind
gequotet, `parse_loose()` wird nicht gebraucht. Geschnitten wird er mit demselben
Klammer-Scanner (`probe_listing.extract_balanced`).

| Typ | Schlüssel | Felder |
|---:|---|---|
| `3` | `item_id` | `name_<lang>`, `quality`, `icon`, `jsonequip` (Preise, Tempo, …) |
| `6` | `spell_id` | `name_<lang>`, `icon`, `rank_<lang>`, **`description_<lang>`**, `skillcategory` |

> ⚠️ **Der Feldname trägt das Sprachkürzel**: `description_dede` gegen `/forever/de/`,
> `description_enus` gegen `/forever/`. Ein fest verdrahteter Feldname schlägt beim
> Sprachwechsel still fehl. `spell_descriptions.description_of()` sucht deshalb nach dem
> Präfix `description_`.

### Die Zauberbeschreibung — Risiko 3 aus dem Plan

Die Frage war: Steht der Zahlenwert aus „+35 Beweglichkeit" irgendwo in den Daten? Er steht
nicht im Namen (`Handschuhe - Überragende Beweglichkeit`), aber in der Beschreibung:

```
25080  Handschuhe - Überragende Beweglichkeit
       Handschuhe dauerhaft verzaubern, sodass die Beweglichkeit um 15 erhöht wird.
       Permanently enchant gloves to increase agility by 15.
```

Abdeckung (`tools/analysis/spell_descriptions.py`, nur echte Rezepte, Berufsränge heraus):

| Beruf | Rezepte | im Block `6` | mit Beschreibung | davon mit Zahl |
|---|---:|---:|---:|---:|
| Verzauberkunst | 261 | 261 | **223 (85,4 %)** | 172 |
| Bergbau | 18 | 18 | 15 (83,3 %) | 0 |
| Alchemie | 194 | 194 | 16 (8,2 %) | 1 |
| Ingenieurskunst | 273 | 273 | 10 (3,7 %) | 3 |
| Schneiderei | 469 | 469 | 5 (1,1 %) | 1 |
| Schmiedekunst | 502 | 502 | 4 (0,8 %) | 0 |
| Lederverarbeitung | 602 | 602 | 3 (0,5 %) | 0 |

**Risiko 3 ist entschärft — aber nicht, weil die Beschreibung überall da wäre.** Sie ist fast
nur bei Verzauberkunst da. Das genügt, weil die Fragenklasse „+35 Beweglichkeit" genau dort
auftritt: Verzauberungen heißen nach ihrem Effekt, Handwerksprodukte nach sich selbst. Nach
einer Wollstofftasche fragt niemand über ihre Werte.

Die Spalte „im Block `6`" ist bei jedem Beruf gleich der Rezeptanzahl: **jeder Zauber aus dem
Listing steht auch im Gatherer-Block.** Handarbeit für die Verzauberungs-Aliase (der
Nein-Fall aus dem Plan) entfällt damit.

### Folge für die zwei Scrape-Ziele

Der Plan sieht einen **zweiten Scrape** über `/forever/items/recipes/<kategorie>` vor, um an
Item-Daten zu kommen. Der Item-Block macht ihn überflüssig: Er enthält **alle** Item-IDs, die
in `reagents` und `creates` vorkommen, mit Namen, Qualität und Icon.

| Beruf | gebrauchte Item-IDs | im Block `3` vorhanden |
|---|---:|---:|
| Verzauberkunst | 180 | 180 |
| Schneiderei | 519 | 519 |
| Schmiedekunst | 548 | 548 |

Das ist kein Zufall, sondern Konstruktion: Wowhead bettet genau die Tooltips ein, die auf der
Seite referenziert werden. **Ein Request pro Beruf und Sprache reicht damit für Rezept,
Produkt, Reagenzien, Icon und Beschreibung.** Der zweite Scrape entfällt — und mit ihm die
Kappung bei 1.000 Einträgen aus Abschnitt 1.

> Was der Item-Block **nicht** repariert: die 72 Rezepte ohne `creates` (Abschnitt 4). Ohne
> `item_id` gibt es nichts nachzuschlagen. Der Produktname aus `name` bleibt dort die
> einzige Quelle.

---

## 7. Noch offen

| Frage | Warum sie zählt |
|---|---|
| Gilt die Tiefenanalyse (Abschnitte 2–5) auch für die anderen sechs Berufe? | Daten liegen vor (Abschnitt 1a), ausgewertet ist nur Schneiderei |
| Wie viele berufsübergreifende Rezepte (`skill` mit mehreren IDs) gibt es? | Dedup im Import |
| Was enthält die Kategorie „Books"? | Falls dort Rezepte primärer Berufe stecken, muss sie in den Scope |
