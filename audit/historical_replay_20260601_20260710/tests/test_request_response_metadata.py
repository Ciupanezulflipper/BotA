from audit.historical_replay_20260601_20260710.src.request_metadata import (
    build_request_metadata,
)
from audit.historical_replay_20260601_20260710.src.response_metadata import (
    capture_response_metadata,
)


def test_request_metadata_redacts_secrets():
    result = build_request_metadata(
        method="get",
        url="https://example.test/data?token=secret&granularity=M15",
        headers={"Authorization": "Bearer secret", "Accept": "application/json"},
    )
    assert "secret" not in result.url
    assert result.headers["Authorization"] == "[REDACTED]"
    assert result.method == "GET"


def test_request_metadata_hashes_body_without_storing_it():
    result = build_request_metadata(
        method="post", url="https://example.test", headers={}, body=b"abc"
    )
    assert result.body_bytes == 3
    assert result.body_sha256 == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_response_metadata_captures_oanda_request_id_and_redacts_cookie():
    result = capture_response_metadata(
        200,
        {
            "RequestID": "abc-123",
            "Content-Type": "application/json",
            "Set-Cookie": "secret-cookie",
        },
    )
    assert result.request_id == "abc-123"
    assert result.content_type == "application/json"
    assert result.headers["Set-Cookie"] == "[REDACTED]"
