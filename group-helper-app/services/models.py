# models/scheduled_deletion.py
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from services.database import Base


class ScheduledDeletion(Base):
    __tablename__ = "scheduled_deletions"

    new_channel_id = Column(Integer, primary_key=True)
    base_channel_id = Column(Integer, nullable=False)
    event_time = Column(DateTime, nullable=False)
    delete_time = Column(DateTime, nullable=False)
    event_title = Column(String, nullable=True)
