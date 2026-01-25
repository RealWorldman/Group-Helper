import sqlite3
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple
from services.models import ScheduledDeletion
from services.database import SessionLocal


def schedule_deletion(channel_id: int,
                      base_channel_id: int,
                      event_time: datetime,
                      delete_at: datetime,
                      event_title: str = None):
    """Speichert einen Löschauftrag in der Datenbank."""
    session = SessionLocal()
    try:
        deletion = ScheduledDeletion(
            new_channel_id=channel_id,
            base_channel_id=base_channel_id,
            event_time=event_time,
            delete_time=delete_at,
            event_title=event_title
        )
        session.add(deletion)
        session.commit()
        logging.info(f"Löschung geplant für Channel {channel_id} um {delete_at}")
    finally:
        session.close()


def get_pending_deletions() -> List[ScheduledDeletion]:
    """Holt alle ausstehenden Löschaufträge."""
    session = SessionLocal()
    try:
        return session.query(ScheduledDeletion).all()
    finally:
        session.close()


def remove_deletion(channel_id: int):
    """Entfernt einen Löschauftrag aus der Datenbank."""
    session = SessionLocal()
    try:
        deletion = session.query(ScheduledDeletion).filter_by(new_channel_id=channel_id).first()
        if deletion:
            session.delete(deletion)
            session.commit()
            logging.info(f"Lösch-Eintrag für Channel {channel_id} entfernt")
    except Exception as e:
        session.rollback()
        logging.error(f"Fehler beim Entfernen des Lösch-Eintrags: {e}")
        raise
    finally:
        session.close()

