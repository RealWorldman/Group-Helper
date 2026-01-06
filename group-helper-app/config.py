"""
Konfigurationsdatei für den Group Helper Bot
"""
from datetime import timezone, timedelta

# Zeitzone
UTC_PLUS_ONE = timezone(timedelta(hours=1))

# Channel wird nach X Stunden gelöscht
DELETE_DELAY_HOURS = 1

# Raid Helper Template ID für Events
RAID_HELPER_TEMPLATE_ID = 2

# Trigger-Zeichen
TRIGGER_SIGN = '🎧'

# Debug-Modus
DEBUG = True

# Debug Guild ID (nur für Entwicklung)
DEBUG_GUILD_ID = 1363983518790713460
