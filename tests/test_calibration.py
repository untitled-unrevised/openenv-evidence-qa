import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[1] / "scripts/calibrate.py"
spec = importlib.util.spec_from_file_location("calibrate", path)
calibrate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibrate)


def test_json_actions_reject_prose_duplicates_and_nonfinite_values():
    assert calibrate.parse_action('{"finish":true}').operation == "finish"
    assert calibrate.parse_action('{"action":{"operation":"list"}}').operation == "list"
    for text in ('```json\n{"operation":"list"}\n```',
                 '{"operation":"list","operation":"finish"}',
                 '{"operation":"submit","answer":{"x":NaN}}',
                 '{"operation":"exec","path":"/etc/passwd"}'):
        with pytest.raises(ValueError):
            calibrate.parse_action(text)


def test_request_caps_and_token_reservations():
    b = calibrate.Budget(max_requests=1, tokens=10)
    b.reserve(10)
    with pytest.raises(RuntimeError):
        b.reserve(1)
    assert b.requests == 1 and b.reserved_tokens == 10
    b = calibrate.Budget(tokens=9)
    with pytest.raises(RuntimeError):
        b.reserve(10)
    assert b.requests == 0


def test_pacing_uses_clock_without_real_waits():
    waits = []
    b = calibrate.Budget(rpm=4)
    b.reserve(1, clock=lambda: 100, sleep=waits.append)
    b.reserve(1, clock=lambda: 103, sleep=waits.append)
    assert waits == [12]


def test_429_stops_without_retries_or_exposing_response(monkeypatch):
    calls = []
    class Response:
        status_code = 429
    def post(*args, **kwargs):
        calls.append(kwargs)
        return Response()
    monkeypatch.setattr(calibrate.requests, "post", post)
    b = calibrate.Budget()
    with pytest.raises(RuntimeError, match="HTTP 429"):
        calibrate.request_reply("https://example.invalid", "dummy", "dummy", [], b)
    assert len(calls) == 1 and b.requests == 1
    assert calls[0]["allow_redirects"] is False
