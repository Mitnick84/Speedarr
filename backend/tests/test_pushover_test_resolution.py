"""POST /api/settings/test/pushover never resolves a typed user key from the saved config (audit NEW-8).

The Pushover branch of test_connection resolves each masked field on its own (`use_existing or
field == REDACTED`). With `use_existing=False`, a freshly typed user key must be used as-is even
when the api token is masked and resolved from the saved config -- never the saved user key.
Characterisation: the backend was already right; the false success came from the UI sending
use_existing=True. Pattern: test_telegram_test_resolution.py.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.api import settings
from app.config import (
    SpeedarrConfig, BandwidthConfig, DownloadBandwidthConfig, UploadBandwidthConfig,
    StreamBandwidthConfig, NotificationsConfig, PushoverNotificationConfig, REDACTED,
)


class _FakeResponse:
    status = 200

    async def text(self):
        return ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    posted = []

    def post(self, url, **kwargs):
        _FakeSession.posted.append((url, kwargs.get("data")))
        return _FakeResponse()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _config(user_key="AUDITMARK-saved-user", api_token="AUDITMARK-saved-token"):
    return SpeedarrConfig(
        bandwidth=BandwidthConfig(
            download=DownloadBandwidthConfig(total_limit=100.0),
            upload=UploadBandwidthConfig(total_limit=50.0),
            streams=StreamBandwidthConfig(),
        ),
        notifications=NotificationsConfig(
            pushover=PushoverNotificationConfig(enabled=True, user_key=user_key, api_token=api_token)
        ),
    )


def _request(config):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(config=config)))


@pytest.fixture(autouse=True)
def _reset_posts():
    _FakeSession.posted.clear()


async def _call(config, body, use_existing=False):
    req = settings.TestConnectionRequest(config=body, use_existing=use_existing)
    with patch("aiohttp.ClientSession", _FakeSession):
        return await settings.test_connection("pushover", req, _request(config), current_user=None)


async def test_typed_user_key_with_masked_token_uses_the_typed_key_and_the_saved_token():
    resp = await _call(
        _config(),
        {"user_key": "AUDITMARK-typed-user", "api_token": REDACTED},
        use_existing=False,
    )
    assert resp.success is True
    assert len(_FakeSession.posted) == 1
    url, payload = _FakeSession.posted[0]
    assert url == "https://api.pushover.net/1/messages.json"
    assert payload["user"] == "AUDITMARK-typed-user"
    assert payload["token"] == "AUDITMARK-saved-token"
