"""
Validierungsfunktionen für Eingaben des Group Helper Bots
"""
from datetime import datetime
import re


def validate_and_parse_date(date_str: str) -> tuple[datetime | None, str | None]:
    """
    Validiert und parsed verschiedene Datumsformate.

    Unterstützte Formate:
    - YYYY-MM-DD (2025-10-25)
    - DD.MM.YYYY (25.10.2025)
    - DD/MM/YYYY (25/10/2025)
    - DD-MM-YYYY (25-10-2025)

    Returns:
        tuple: (parsed_date, error_message)
    """
    if not date_str or not isinstance(date_str, str):
        return None, "Datum fehlt oder ist ungültig."

    date_str = date_str.strip()

    # Verschiedene Datumsformate probieren
    date_formats = [
        ('%Y-%m-%d', 'YYYY-MM-DD'),      # 2025-10-25
        ('%d.%m.%Y', 'DD.MM.YYYY'),      # 25.10.2025
        ('%d/%m/%Y', 'DD/MM/YYYY'),      # 25/10/2025
        ('%d-%m-%Y', 'DD-MM-YYYY'),      # 25-10-2025
        ('%Y/%m/%d', 'YYYY/MM/DD'),      # 2025/10/25
    ]

    for date_format, format_name in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, date_format)
            return parsed_date, None
        except ValueError:
            continue

    # Wenn kein Format passt
    return None, (
        f"Ungültiges Datumsformat: `{date_str}`\n"
        f"Erlaubte Formate: **YYYY-MM-DD**, **DD.MM.YYYY**, **DD/MM/YYYY**, **DD-MM-YYYY**\n"
        f"Beispiele: 2025-10-25, 25.10.2025, 25/10/2025"
    )


def validate_and_parse_time(time_str: str) -> tuple[tuple[int, int] | None, str | None]:
    """
    Validiert und parsed verschiedene Zeitformate.

    Unterstützte Formate:
    - HH:MM (20:00, 08:30)
    - H:MM (8:30)
    - HH.MM (20.00)
    - HHMM (2000)

    Returns:
        tuple: ((hour, minute), error_message)
    """
    if not time_str or not isinstance(time_str, str):
        return None, "Zeit fehlt oder ist ungültig."

    time_str = time_str.strip()

    # Format: HH:MM oder H:MM
    if ':' in time_str:
        match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
        else:
            return None, f"Ungültiges Zeitformat: `{time_str}` (erwarte **HH:MM**)"

    # Format: HH.MM
    elif '.' in time_str:
        match = re.match(r'^(\d{1,2})\.(\d{2})$', time_str)
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
        else:
            return None, f"Ungültiges Zeitformat: `{time_str}` (erwarte **HH.MM**)"

    # Format: HHMM
    elif len(time_str) in [3, 4] and time_str.isdigit():
        if len(time_str) == 4:
            hour, minute = int(time_str[:2]), int(time_str[2:])
        else:
            hour, minute = int(time_str[0]), int(time_str[1:])
    else:
        return None, (
            f"Ungültiges Zeitformat: `{time_str}`\n"
            f"Erlaubte Formate: **HH:MM**, **HH.MM**, **HHMM**\n"
            f"Beispiele: 20:00, 20.00, 2000, 8:30"
        )

    # Validierung der Werte
    if not (0 <= hour <= 23):
        return None, f"Ungültige Stunde: {hour} (muss zwischen 0 und 23 liegen)"
    if not (0 <= minute <= 59):
        return None, f"Ungültige Minute: {minute} (muss zwischen 0 und 59 liegen)"

    return (hour, minute), None


def validate_title(title: str) -> tuple[bool, str | None]:
    """
    Validiert den Event-Titel.

    Returns:
        tuple: (is_valid, error_message)
    """
    if not title or not isinstance(title, str):
        return False, "Titel fehlt."

    title = title.strip()

    if len(title) < 3:
        return False, "Titel muss mindestens 3 Zeichen lang sein."

    if len(title) > 100:
        return False, "Titel darf maximal 100 Zeichen lang sein."

    # Ungültige Zeichen für Discord Channel-Namen
    invalid_chars = ['@', '#', ':', '```', 'discord']
    for char in invalid_chars:
        if char.lower() in title.lower():
            return False, f"Titel darf '{char}' nicht enthalten."

    return True, None


def validate_description(desc: str) -> tuple[bool, str | None]:
    """
    Validiert die Event-Beschreibung.

    Returns:
        tuple: (is_valid, error_message)
    """
    if not desc or not isinstance(desc, str):
        return False, "Beschreibung fehlt."

    desc = desc.strip()

    if len(desc) < 3:
        return False, "Beschreibung muss mindestens 3 Zeichen lang sein."

    if len(desc) > 1000:
        return False, "Beschreibung darf maximal 1000 Zeichen lang sein."

    return True, None

