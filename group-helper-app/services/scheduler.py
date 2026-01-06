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
                      delete_at: datetime,
                      event_time: datetime,
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
        session.merge(deletion)
        session.commit()
        logging.info(f"Löschung geplant für Channel {channel_id} um {delete_at}")
    finally:
        session.close()


def get_pending_deletions() -> List[ScheduledDeletion]:
    """Holt alle ausstehenden Löschaufträge."""
    session = SessionLocal()
    return session.query(ScheduledDeletion).all()


def remove_deletion(channel_id: int):
    """Entfernt einen Löschauftrag aus der Datenbank."""
    session = SessionLocal()
    try:
        deletion = session.query(ScheduledDeletion).filter_by(new_channel_id=channel_id).first()
        if deletion:
            session.delete(deletion)
            session.commit()
            logging.info(f"Löschauftrag für Channel {channel_id} entfernt")
    finally:
        session.close()

