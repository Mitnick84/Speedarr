"""mask_stored decides by key and fails closed (audit NEW-10)."""
import json

import pytest

from app.config import REDACTED, mask_stored


def test_json_row_masks_leaves_and_keeps_the_rest():
    row = json.dumps([{"id": "qb", "password": "AUDITMARK-pass", "url": "u"}])
    assert json.loads(mask_stored("download_clients", row)) == [{"id": "qb", "password": REDACTED, "url": "u"}]


def test_secret_key_is_redacted_whatever_the_text_looks_like():
    assert mask_stored("notifications.ntfy.topic", '"AUDITMARK-topic"') == REDACTED
    assert mask_stored("notifications.ntfy.topic", "AUDITMARK-topic") == REDACTED


@pytest.mark.parametrize("text", ["not json AUDITMARK-x", '"a string"', "42"])
def test_unparseable_or_non_container_json_row_fails_closed(text):
    assert mask_stored("download_clients", text) == REDACTED


@pytest.mark.parametrize("key, text", [
    ("download_clients", '{"password":"AUDITMARK-dict"}'),
    ("media_servers", '[["AUDITMARK-nested"]]'),
    ("notifications.ntfy", '["AUDITMARK-list"]'),
])
def test_wrong_shaped_container_fails_closed(key, text):
    assert mask_stored(key, text) == REDACTED


def test_list_with_a_non_dict_item_fails_closed():
    assert mask_stored("download_clients", '[{"id":"qb"}, "AUDITMARK-item"]') == REDACTED


def test_correctly_shaped_dict_masks_only_the_leaf():
    row = json.dumps({"topic": "AUDITMARK-topic", "server": "https://ntfy.sh"})
    assert json.loads(mask_stored("notifications.ntfy", row)) == {"topic": REDACTED, "server": "https://ntfy.sh"}


def test_correctly_shaped_media_server_list_masks_only_the_leaf():
    row = json.dumps([{"id": "p", "token": "AUDITMARK-tok", "url": "u"}])
    assert json.loads(mask_stored("media_servers", row)) == [{"id": "p", "token": REDACTED, "url": "u"}]


def test_non_secret_key_is_unchanged():
    assert mask_stored("system.log_level", "DEBUG") == "DEBUG"


@pytest.mark.parametrize("value", [None, "", "[DELETED]", "None"])
@pytest.mark.parametrize("key", ["download_clients", "plex.token", "system.log_level"])
def test_pass_through_values_are_unchanged(key, value):
    assert mask_stored(key, value) == value
