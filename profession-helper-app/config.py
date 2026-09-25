"""
Konstanten und ENV-Overrides.

Alles, was sich zwischen Entwicklungsrechner und Raspberry Pi unterscheidet, steht
hier und nur hier. Die Pfade sind bewusst **absolut aus dem Dateiort abgeleitet**,
nicht relativ zum Arbeitsverzeichnis: Unter systemd ist das CWD nicht das
Projektverzeichnis, und ein relativer Pfad legt dann still eine leere Datenbank am
falschen Ort an. Genau dieser Fehler steckt im Nachbarprojekt
(group-helper-app/services/database.py) und wird hier nicht geerbt.
"""

import os
from pathlib import Path

# config.py liegt direkt in der Projektwurzel.
BASE_DIR = Path(__file__).resolve().parent


def _env_path(name: str, default: Path) -> Path:
    """Pfad aus der Umgebung, sonst der Vorgabewert - immer absolut."""
    raw = os.getenv(name)
    return Path(raw).expanduser().resolve() if raw else default


def _env_flag(name: str, default: bool = False) -> bool:
    """Schalter aus der Umgebung. Alles ausser den bekannten Ja-Werten ist Nein."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().casefold() in {"1", "true", "yes", "ja", "on"}


def _env_int(name: str) -> int | None:
    """Zahl aus der Umgebung, oder None wenn nicht gesetzt oder leer."""
    raw = os.getenv(name)
    return int(raw) if raw and raw.strip() else None


# --- Pfade ------------------------------------------------------------------

DATA_DIR = _env_path("PROFESSION_DATA_DIR", BASE_DIR / "data")
DB_PATH = _env_path("PROFESSION_DB_PATH", DATA_DIR / "profession_helper.db")
LOG_DIR = _env_path("PROFESSION_LOG_DIR", BASE_DIR / "logs")

# Katalog-Artefakte: current.json ist der aktive Stand, snapshots/ die Historie.
CATALOG_DIR = DATA_DIR / "catalog"
CATALOG_CURRENT = CATALOG_DIR / "current.json"
CATALOG_SNAPSHOT_DIR = CATALOG_DIR / "snapshots"
PROBE_DIR = DATA_DIR / "probe"

# Handgepflegte Dateien, die den automatischen Katalog korrigieren bzw. ergaenzen.
ALIASES_FILE = CATALOG_DIR / "aliases.de.yaml"
OVERRIDES_FILE = CATALOG_DIR / "overrides.yaml"


# --- Discord ----------------------------------------------------------------

# Im DEBUG-Modus wird der Command-Tree nur in diese eine Gilde synchronisiert.
# Das ist sofort sichtbar, waehrend ein globaler Sync bis zu einer Stunde braucht.
DEBUG = _env_flag("DEBUG")
DEBUG_GUILD_ID = _env_int("DEBUG_GUILD_ID")

# Rolle, die fremde Charaktere bearbeiten und /admin benutzen darf.
ADMIN_ROLE_NAME = os.getenv("PROFESSION_ADMIN_ROLE", "Gildenleitung")


# --- Scraper ----------------------------------------------------------------

WOWHEAD_BASE_URL = "https://www.wowhead.com/forever"

# Nicht verhandelbar, siehe tools/catalog_sources.md: hoechstens ein Request pro
# Sekunde, und ein User-Agent, der sagt wer wir sind - keine Browser-Tarnung.
WOWHEAD_RATE_LIMIT_SECONDS = 1.0
WOWHEAD_USER_AGENT = (
    "profession-helper-app/0.1 (privates Gilden-Tool; yves.etter18@gmail.com)"
)
HTTP_TIMEOUT_SECONDS = 20.0


# --- LLM (M4, hier nur als Schalter vorhanden) ------------------------------

# Beide standardmaessig aus. Der Bot muss ohne LLM vollstaendig benutzbar sein;
# der Intent-Layer ist Komfort, kein Fundament.
ENABLE_LLM = _env_flag("ENABLE_LLM")
ALLOW_LLM_SQL = _env_flag("ALLOW_LLM_SQL")
