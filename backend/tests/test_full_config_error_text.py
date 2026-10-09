"""A rejected full-config write names the failing field, never the config's values (audit NEW-12).

str() of the ValidationError echoes input_value, and the input is the whole config including
decrypted secrets.
"""
from types import SimpleNamespace

import pytest

from app.services.config_manager import ConfigManager


def _manager():
    return ConfigManager(SimpleNamespace(state=SimpleNamespace(
        config=None, polling_monitor=None, decision_engine=None,
        controller_manager=None, notification_service=None)))


async def test_invalid_full_config_error_omits_secrets_and_names_the_field(db):
    config = {
        "download_clients": [{
            "id": "qb1", "type": "qbittorrent", "name": "qB", "url": "http://qb:8080",
            "username": "admin", "password": "AUDITMARK-full-pass",
        }],
        "system": {"log_level": "LOUD"},
    }

    with pytest.raises(ValueError) as exc:
        await _manager().update_full_config(config, db)

    text = str(exc.value)
    assert "AUDITMARK-full-pass" not in text
    assert "input_value" not in text
    assert "system.log_level" in text
