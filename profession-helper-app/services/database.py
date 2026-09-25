"""
Engine, Session-Fabrik und die gemeinsame Basis aller Modelle.

Neu geschrieben statt aus group-helper-app kopiert. Zwei Fehler werden dort nicht
geerbt:

* `DB_PATH = Path("data/...")` ist relativ zum Arbeitsverzeichnis und legt unter
  systemd still eine leere Datenbank am falschen Ort an. Hier kommt die Verbindung
  aus `config.DATABASE_URL`, und ohne gesetzte Variable bricht der Start mit
  einer Meldung ab, die sagt was zu tun ist.
* `sqlalchemy.ext.declarative.declarative_base` ist in SQLAlchemy 2.0 veraltet.
  Hier: `class Base(DeclarativeBase)`.

Die Engine wird **beim ersten Zugriff** gebaut, nicht beim Import. Sonst koennte
kein Test und kein Hilfsskript dieses Modul importieren, ohne eine erreichbare
Datenbank zu haben.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

import config


class Base(DeclarativeBase):
    """Gemeinsame Basis aller ORM-Modelle."""


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """
    Die Engine dieses Prozesses, beim ersten Aufruf erzeugt.

    Das Pooling-Setup stammt aus dem Nachbarprojekt und passt hier besser als
    dort: Postgres haelt echte Verbindungen, `pool_pre_ping` faengt die ab, die
    ueber Nacht weggestorben sind.
    """
    global _engine
    if _engine is None:
        if not config.DATABASE_URL:
            raise RuntimeError(
                "PROFESSION_DATABASE_URL ist nicht gesetzt.\n"
                "Erwartet wird z. B. "
                "postgresql+psycopg://benutzer@host:5432/group-helper"
            )
        _engine = create_engine(
            config.DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Die Session-Fabrik dieses Prozesses, beim ersten Aufruf erzeugt."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Eine Session mit Commit, Rollback und Close - ohne dass der Aufrufer daran
    denken muss.

    Ersetzt das haendische try/commit/rollback/close aus
    group-helper-app/services/scheduler.py. **Nur aus Threads aufrufen, nie
    direkt aus einem async-Handler** - das DAO ist synchron und wuerde den
    Event-Loop blockieren. Der Weg dorthin ist `await asyncio.to_thread(...)`.
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """
    Verwirft Engine und Session-Fabrik.

    Nur fuer Tests und fuer Skripte, die die Verbindung wechseln; im Botbetrieb
    gibt es keinen Grund dafuer.
    """
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
