"""
Tests fuer utils/secrets.py.

Der Aufbau der Testdatei entspricht der echten secrets.json des Nachbarbots -
inklusive der Eigenart, dass IDs mal als Zahl und mal als Zeichenkette
dortstehen.
"""

import json
import logging

import pytest

from utils import secrets

BEISPIEL = {
    "DISCORD": [
        {"AppName": "discord-group-helper-app-token", "DiscordToken": "token-raid"},
        {"AppName": "discord-profession-helper-app-token", "DiscordToken": "token-berufe"},
        {"AppName": "app-ohne-token"},
    ],
    # ServerID als Zahl - im Nachbarbot steht sie mal so, mal als Zeichenkette.
    "RAID-HELPER": [{"ServerID": 123456789, "ApiKey": "api-key"}],
}


@pytest.fixture(autouse=True)
def leerer_zwischenspeicher():
    """Ohne das wuerde ein Test die Datei des vorherigen sehen."""
    secrets.clear_cache()
    yield
    secrets.clear_cache()


@pytest.fixture
def datei(tmp_path):
    pfad = tmp_path / "secrets.json"
    pfad.write_text(json.dumps(BEISPIEL), encoding="utf-8")
    return pfad


def test_findet_den_richtigen_token(datei) -> None:
    assert secrets.get_discord_token("discord-profession-helper-app-token", datei) == "token-berufe"
    assert secrets.get_discord_token("discord-group-helper-app-token", datei) == "token-raid"


def test_id_als_zahl_und_als_text_treffen_beide(datei) -> None:
    """In der Datei steht 123456789 als Zahl; gesucht wird mit einer Zeichenkette."""
    assert secrets.get_secret("RAID-HELPER", "ServerID", "123456789", "ApiKey", datei) == "api-key"
    assert secrets.get_secret("RAID-HELPER", "ServerID", 123456789, "ApiKey", datei) == "api-key"


def test_unbekannter_eintrag_ergibt_none(datei) -> None:
    assert secrets.get_secret("DISCORD", "AppName", "gibt-es-nicht", "DiscordToken", datei) is None


def test_eintrag_ohne_das_gesuchte_feld_ergibt_none(datei) -> None:
    assert secrets.get_secret("DISCORD", "AppName", "app-ohne-token", "DiscordToken", datei) is None


def test_unbekannter_abschnitt_ergibt_none(datei) -> None:
    assert secrets.get_secret("GIBT-ES-NICHT", "a", "b", "c", datei) is None


def test_fehlende_datei_ergibt_leeres_dict(tmp_path) -> None:
    assert secrets.load_secrets(tmp_path / "fehlt.json") == {}


def test_kaputtes_json_ergibt_leeres_dict(tmp_path) -> None:
    pfad = tmp_path / "kaputt.json"
    pfad.write_text("{ das ist kein json", encoding="utf-8")
    assert secrets.load_secrets(pfad) == {}


def test_require_secret_bricht_mit_verwertbarer_meldung_ab(datei) -> None:
    """
    Die Meldung muss sagen, wo gesucht wurde - sonst steht man vor einem
    'KeyError: DiscordToken' und raet, welche Datei gemeint ist.
    """
    with pytest.raises(RuntimeError) as fehler:
        secrets.require_secret("DISCORD", "AppName", "gibt-es-nicht", "DiscordToken", datei)
    meldung = str(fehler.value)
    assert "DiscordToken" in meldung
    assert "gibt-es-nicht" in meldung
    assert str(datei) in meldung


def test_datei_wird_nur_einmal_gelesen(datei) -> None:
    """Das Original liest bei jedem Zugriff neu und loggt dabei jedes Mal."""
    secrets.load_secrets(datei)
    datei.write_text(json.dumps({"DISCORD": []}), encoding="utf-8")
    assert secrets.get_discord_token("discord-profession-helper-app-token", datei) == "token-berufe"


def test_der_wert_landet_nicht_im_log(datei, caplog) -> None:
    """
    Die wichtigste Zusicherung dieser Datei: Ein Token darf nie in bot.log
    stehen. Die Logs werden 30 Tage aufbewahrt.
    """
    with caplog.at_level(logging.DEBUG):
        secrets.get_discord_token("discord-profession-helper-app-token", datei)
    assert "token-berufe" not in caplog.text
