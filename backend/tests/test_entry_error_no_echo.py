"""A list-PUT entry error never echoes the resolved secret (audit NEW-14).

Before: update_download_clients / update_media_servers put str(ValidationError) in the 400 detail; Pydantic
includes input_value, which for a missing field is the whole entry dict, by then holding the stored,
decrypted password / api_key / token.
"""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import BaseModel, model_validator

from app.api.settings import (
    DownloadClientsUpdateRequest, MediaServersUpdateRequest, update_download_clients, update_media_servers,
)
from app.config import (
    SpeedarrConfig, BandwidthConfig, DownloadBandwidthConfig, UploadBandwidthConfig, StreamBandwidthConfig,
    DownloadClientConfig, MediaServerConfig, REDACTED, validation_detail,
)

QB = {"id": "qb_1", "type": "qbittorrent", "name": "Seedbox", "url": "http://qb:8080", "username": "u",
      "password": "AUDITMARK-qb-pass"}
SAB = {"id": "sab_1", "type": "sabnzbd", "name": "Usenet", "url": "http://sab:8080",
       "api_key": "AUDITMARK-sab-key", "max_speed_mbps": 100.0}
PLEX = {"id": "plex_1", "name": "Plex", "type": "plex", "url": "http://plex:32400", "token": "AUDITMARK-plex-token"}


class _ConfigManager:
    async def update_full_config(self, config_data, db, user_id=None):
        return SpeedarrConfig(**config_data)

    async def _reload_services(self, section_name, config):
        pass


def _request():
    config = SpeedarrConfig(
        bandwidth=BandwidthConfig(
            download=DownloadBandwidthConfig(total_limit=100.0),
            upload=UploadBandwidthConfig(total_limit=50.0),
            streams=StreamBandwidthConfig(),
        ),
        download_clients=[DownloadClientConfig(**QB), DownloadClientConfig(**SAB)],
        media_servers=[MediaServerConfig(**PLEX)],
    )
    state = SimpleNamespace(config=config, config_manager=_ConfigManager(), controller_manager=None,
                            polling_monitor=None)
    return SimpleNamespace(app=SimpleNamespace(state=state))


async def _put_clients(clients):
    return await update_download_clients(
        DownloadClientsUpdateRequest(clients=clients), request=_request(), db=None,
        current_user=SimpleNamespace(id=1),
    )


async def _put_servers(servers):
    return await update_media_servers(
        MediaServersUpdateRequest(servers=servers), request=_request(), db=None,
        current_user=SimpleNamespace(id=1),
    )


@pytest.mark.parametrize("entry, field, secret, other", [
    (QB, "password", "AUDITMARK-qb-pass", SAB),
    (SAB, "api_key", "AUDITMARK-sab-key", QB),
])
async def test_client_entry_error_does_not_echo_the_stored_secret(entry, field, secret, other):
    broken = {k: v for k, v in entry.items() if k != "name"}
    broken[field] = REDACTED
    with pytest.raises(HTTPException) as exc:
        await _put_clients([broken, dict(other)])
    assert exc.value.status_code == 400
    assert exc.value.detail.startswith("Invalid client configuration for")
    assert "name: Field required" in exc.value.detail
    assert secret not in exc.value.detail
    assert "input_value" not in exc.value.detail


async def test_media_server_entry_error_does_not_echo_the_stored_token():
    with pytest.raises(HTTPException) as exc:
        await _put_servers([{**PLEX, "token": REDACTED, "enabled": "not-a-bool"}])
    assert exc.value.status_code == 400
    assert exc.value.detail.startswith("Invalid media server")
    assert "enabled:" in exc.value.detail
    assert "AUDITMARK-plex-token" not in exc.value.detail
    assert "input_value" not in exc.value.detail


# --- validation_detail ---------------------------------------------------------------------------------

class _Inner(BaseModel):
    b: int


class _Outer(BaseModel):
    a: list[_Inner]


class _Whole(BaseModel):
    x: int = 0

    @model_validator(mode="after")
    def _never(self):
        raise ValueError("whole model is wrong")


def _validation_error(model, **data):
    with pytest.raises(Exception) as exc:
        model(**data)
    return exc.value


def test_validation_detail_joins_a_nested_loc():
    err = _validation_error(_Outer, a=[{"b": "AUDITMARK-nested"}])
    detail = validation_detail(err)
    assert detail.startswith("a.0.b: ")
    assert "AUDITMARK-nested" not in detail
    assert "input_value" not in detail


def test_validation_detail_empty_loc_contributes_just_the_message():
    detail = validation_detail(_validation_error(_Whole))
    assert detail == "Value error, whole model is wrong"
    assert "input_value" not in detail


def test_validation_detail_joins_several_errors():
    detail = validation_detail(_validation_error(_Outer, a=[{}, {"b": "x"}]))
    assert detail.count("; ") == 1
    assert detail.startswith("a.0.b: Field required; a.1.b: ")


def test_validation_detail_of_any_other_exception_is_str():
    assert validation_detail(ValueError("x")) == "x"
