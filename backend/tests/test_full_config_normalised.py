"""A full-config write stores the validated model, not the raw dict (audit B2-6).

Before: the dict was validated into `new_config` and then flattened raw, so field-validator
normalisation (log level case, LAN network trimming) was thrown away on the way to the database.
"""
from types import SimpleNamespace

from sqlalchemy import select

from app.config import (
    SpeedarrConfig, BandwidthConfig, DownloadBandwidthConfig, UploadBandwidthConfig,
    StreamBandwidthConfig,
)
from app.models.configuration import Configuration
from app.services.config_manager import ConfigManager


def _base():
    return SpeedarrConfig(bandwidth=BandwidthConfig(
        download=DownloadBandwidthConfig(total_limit=100.0),
        upload=UploadBandwidthConfig(total_limit=50.0),
        streams=StreamBandwidthConfig(),
    ))


def _manager():
    return ConfigManager(SimpleNamespace(state=SimpleNamespace(
        config=None, polling_monitor=None, decision_engine=None,
        controller_manager=None, notification_service=None)))


async def _row(db, key):
    return (await db.execute(select(Configuration).where(Configuration.key == key))).scalar_one_or_none()


async def test_full_config_write_stores_the_normalised_values(db):
    cm = _manager()
    await cm.migrate_yaml_to_db(_base(), db)
    raw = _base().model_dump()
    raw["system"]["log_level"] = "debug"
    raw["media_servers"] = [{
        "id": "ms1", "name": "Plex", "type": "plex", "url": "http://plex:32400",
        "lan_networks": " 10.0.0.0/24 , ,192.168.1.5 ",
    }]

    await cm.update_full_config(raw, db)

    assert (await _row(db, "system.log_level")).value == "DEBUG"
    lan = await _row(db, "media_servers")
    assert lan is not None and " 10.0.0.0/24" not in lan.value and "10.0.0.0/24" in lan.value
    assert " ," not in lan.value


async def test_full_config_write_leaves_no_legacy_section_rows(db):
    cm = _manager()
    await cm.migrate_yaml_to_db(_base(), db)

    await cm.update_full_config(_base().model_dump(), db)

    assert await _row(db, "qbittorrent") is None
    assert await _row(db, "sabnzbd") is None
