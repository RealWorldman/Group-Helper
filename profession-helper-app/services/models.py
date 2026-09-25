"""
ORM-Abbildung der Tabellen aus services/migrations.py.

**Diese Datei legt nichts an.** Das Schema entsteht ausschliesslich aus den
Migrationen; hier steht nur, wie Python die vorhandenen Tabellen sieht. Wer eine
Spalte braucht, schreibt zuerst eine Migration und traegt sie danach hier nach -
nie umgekehrt.

Dass beides auseinanderlaufen kann, ist der Preis dafuer, das DDL lesbar zu
halten. Dagegen hilft `tools/check_schema.py`: Es vergleicht diese Modelle mit
der laufenden Datenbank und meldet jede Abweichung.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.database import Base


class Profession(Base):
    """Einer der neun Berufe im Scope. Stammdaten, gepflegt per Migration."""

    __tablename__ = "professions"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    key: Mapped[str] = mapped_column(Text, unique=True)
    name_de: Mapped[str] = mapped_column(Text)
    name_en: Mapped[str] = mapped_column(Text)
    # Aus dem Wowhead-Feld `skill`, z. B. 197 fuer Schneiderei.
    skill_line_id: Mapped[int] = mapped_column(Integer, unique=True)
    wowhead_slug: Mapped[str] = mapped_column(Text, unique=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    has_recipes: Mapped[bool] = mapped_column(Boolean, default=True)
    is_included: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Profession {self.key} skill={self.skill_line_id}>"


class Guild(Base):
    """Eine Discord-Gilde. Die id ist die Snowflake, nicht selbst vergeben."""

    __tablename__ = "guilds"

    # autoincrement=False, weil Discord die Nummer liefert. Ohne das haelt
    # SQLAlchemy den bigint-Primaerschluessel fuer eine Sequenz.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    members: Mapped[list["Member"]] = relationship(back_populates="guild")

    def __repr__(self) -> str:
        return f"<Guild {self.id} {self.name!r}>"


class Member(Base):
    """
    Ein Discord-Nutzer in einer Gilde.

    Traegt die Twinks: Ergebnisse werden nach Mitglied gruppiert, nicht nach
    Charakter - sonst steht derselbe Mensch dreimal in einer Antwort.
    """

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guilds.id", ondelete="CASCADE")
    )
    discord_user_id: Mapped[int] = mapped_column(BigInteger)
    display_name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    guild: Mapped["Guild"] = relationship(back_populates="members")
    characters: Mapped[list["Character"]] = relationship(back_populates="member")

    def __repr__(self) -> str:
        return f"<Member {self.display_name!r} discord={self.discord_user_id}>"


class Character(Base):
    """Ein Spielcharakter. Wird nie geloescht, nur auf is_active = False gesetzt."""

    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    member_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("members.id", ondelete="CASCADE")
    )
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guilds.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text)
    # Von utils.textnorm.normalize(). Die Eindeutigkeit haengt hieran, nicht an
    # `name` - sonst waeren "Muehlenbraeu" und "Mühlenbräu" zwei Charaktere.
    name_norm: Mapped[str] = mapped_column(Text)
    realm: Mapped[str] = mapped_column(Text)
    # 'alliance' oder 'horde', per CHECK in der Datenbank erzwungen.
    faction: Mapped[str] = mapped_column(Text)
    # Nicht `class`: das waere in Python ein Schluesselwort.
    wow_class: Mapped[str | None] = mapped_column(Text, default=None)
    level: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Treibt den monatlichen Reminder; aelter als 90 Tage wird im Autocomplete
    # mit einem Warnzeichen markiert.
    last_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    member: Mapped["Member"] = relationship(back_populates="characters")
    professions: Mapped[list["CharacterProfession"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Character {self.name!r}@{self.realm}>"


class CharacterProfession(Base):
    """Ein Beruf eines Charakters, mit erreichtem Skill."""

    __tablename__ = "character_professions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    character_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("characters.id", ondelete="CASCADE")
    )
    profession_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("professions.id"))
    skill_level: Mapped[int] = mapped_column(SmallInteger)
    skill_max: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    specialization: Mapped[str | None] = mapped_column(Text, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    character: Mapped["Character"] = relationship(back_populates="professions")
    profession: Mapped["Profession"] = relationship()

    def __repr__(self) -> str:
        return f"<CharacterProfession char={self.character_id} prof={self.profession_id}>"
