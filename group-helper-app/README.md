# Group-Helper Bot 🎮

Ein Discord-Bot zum Erstellen von Gruppen-Events mit automatischer Channel-Verwaltung und Raid Helper Integration.

## 📋 Features

- **Slash Commands** für einfache Event-Erstellung
- **Automatische Channel-Erstellung** für jedes Event
- **Raid Helper Integration** für Event-Management
- **Automatische Channel-Löschung** nach Event-Ende
- **Zeitzone-Unterstützung** (UTC+1)
- **Input-Validierung** für Datum, Zeit und Beschreibungen

---

## 🚀 Installation

### Voraussetzungen

- Python 3.8 oder höher
- Discord Bot Token
- (Optional) Google Cloud Secret Manager Zugriff
- Raid Helper Bot auf deinem Discord Server

### 1. Repository klonen

```bash
git clone <repository-url>
cd Group-Helper
```

### 2. Abhängigkeiten installieren

```bash
cd group-helper-app
pip install -r requirements.txt
```

Die `requirements.txt` enthält:
- `discord.py==2.3.2`
- `google-cloud-secret-manager==2.23.0`

### 3. Konfiguration

#### Secrets einrichten

Erstelle eine `secrets.json` im Root-Verzeichnis:

```json
{
  "discord-group-helper-app-token": "DEIN_DISCORD_BOT_TOKEN"
}
```

**Alternative:** Nutze Google Cloud Secret Manager (für Production)

#### Bot-Konfiguration anpassen

Bearbeite `config.py` nach deinen Bedürfnissen:

```python
# Zeitzone anpassen
UTC_PLUS_ONE = timezone(timedelta(hours=1))

# Channel-Löschung nach X Stunden
DELETE_DELAY_HOURS = 24

# Raid Helper Template ID
RAID_HELPER_TEMPLATE_ID = 2

# Debug-Modus (nur für Entwicklung)
DEBUG = False
DEBUG_GUILD_ID = 1234567890  # Deine Test-Server ID
```

### 4. Discord Bot erstellen

1. Gehe zu [Discord Developer Portal](https://discord.com/developers/applications)
2. Erstelle eine neue Application
3. Navigiere zu "Bot" und erstelle einen Bot
4. Kopiere den Bot Token in deine `secrets.json`
5. Aktiviere unter "Privileged Gateway Intents":
   - ✅ Message Content Intent
   - ✅ Server Members Intent (optional)

### 5. Bot-Berechtigungen

Dein Bot benötigt folgende Berechtigungen auf dem Discord Server:

- ✅ Manage Channels (Channels erstellen/löschen)
- ✅ Send Messages
- ✅ Read Messages/View Channels
- ✅ Use Slash Commands

**Invite-Link generieren:**
```
https://discord.com/api/oauth2/authorize?client_id=DEINE_CLIENT_ID&permissions=16&scope=bot%20applications.commands
```

### 6. Bot starten

```bash
python group-helper.py
```

Bei erfolgreicher Verbindung siehst du:
```
[INFO] Starte Group Helper Bot...
[INFO] Bot verbunden als YourBotName
[INFO] Slash commands synchronisiert
```

---

## 📖 Verwendung für Discord-User

### Befehle

Der Bot bietet einen Slash Command zum Erstellen von Gruppen-Events:

#### `/group-event` - Event erstellen

Erstellt ein neues Gruppen-Event mit eigenem Channel und Raid Helper Integration.

**Parameter:**
- `date` - Datum des Events (Formate: `YYYY-MM-DD`, `DD.MM.YYYY`, `DD/MM/YYYY`)
- `time` - Uhrzeit (Formate: `HH:MM`, `HH.MM`, `HHMM`)
- `title` - Titel des Events (max. 100 Zeichen)
- `desc` - Beschreibung des Events (max. 1000 Zeichen)

---

## 📋 Copy-Paste Anleitung für Discord

**Kopiere den folgenden Text in deinen Discord-Channel:**

```
🎮 **Group Helper Bot - Anleitung**

Mit dem Group Helper Bot kannst du ganz einfach Gruppen-Events erstellen!

**📌 Befehl:**
`/group-event`

**📝 Beispiel:**

`/group-event date:2025-11-15 time:20:00 title:HC Runs desc:Wir machen ein paar HCs, nichts HRs!`

**✅ Was passiert?**
1. Ein neuer Channel wird automatisch erstellt
2. Ein Raid Helper Event wird im neuen Channel angelegt
3. Der Channel wird 24h nach dem Event automatisch gelöscht

**📅 Datum-Formate:**
- `2025-11-15` (YYYY-MM-DD)
- `15.11.2025` (DD.MM.YYYY)
- `15/11/2025` (DD/MM/YYYY)

**🕐 Zeit-Formate:**
- `20:00` (HH:MM)
- `20.00` (HH.MM)
- `2000` (HHMM)

**💡 Tipps:**
- Events müssen in der Zukunft liegen
- Der Titel sollte kurz und prägnant sein
- In der Beschreibung kannst du alle wichtigen Infos angeben
- Der neue Channel wird nach dem Event-Datum benannt

**❓ Probleme?**
Kontaktiere einen Admin, wenn der Bot nicht reagiert oder Fehler auftreten.
```

---

## 🛠️ Entwicklung

### Debug-Modus aktivieren

In `config.py`:
```python
DEBUG = True
DEBUG_GUILD_ID = 1234567890  # Deine Test-Server ID
```

Im Debug-Modus werden Slash Commands nur auf dem Test-Server synchronisiert (schneller).

### Logging

Logs werden automatisch erstellt in:
- `logs/bot.log` - Allgemeine Bot-Aktivitäten
- `logs/errors.log` - Nur Fehler

### Projekt-Struktur

```
group-helper-app/
├── group-helper.py          # Haupt-Bot-Datei
├── config.py                # Konfiguration
├── validators.py            # Input-Validierung
├── requirements.txt         # Python-Dependencies
├── services/
│   ├── channel_manager.py   # Channel-Verwaltung
│   └── raid_helper.py       # Raid Helper API Integration
└── utils/
    ├── logger.py            # Logging-Setup
    └── secrets.py           # Secret-Management
```

---

## 🔒 Sicherheit

- **Secrets niemals committen!** (`secrets.json` ist in `.gitignore`)
- Bot Token regelmäßig rotieren
- Minimale Bot-Berechtigungen verwenden
- Google Cloud Secret Manager für Production empfohlen

---

## 📝 Lizenz

[Deine Lizenz hier einfügen]

---

## 🤝 Support

Bei Fragen oder Problemen:
- Erstelle ein Issue auf GitHub
- Kontaktiere den Entwickler

---

**Viel Spaß beim Organisieren deiner Gruppen-Events! 🎉**

