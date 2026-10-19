import json

from bookit.api.common.idempotency import build_idempotency_key

URL = "/api/v1/appointments"
BODY = {"service_id": 3, "start_time": 1_893_456_000}


def _post(rf, body, path=URL, **headers):
    data = body if isinstance(body, str) else json.dumps(body)
    return rf.post(path, data=data, content_type="application/json", **headers)


def test_key_ignores_json_key_order_and_spacing(rf):
    first = build_idempotency_key(1, _post(rf, BODY))
    second = build_idempotency_key(1, _post(rf, '{ "start_time": 1893456000,  "service_id": 3 }'))
    assert first == second
    assert len(first) == 64


def test_key_differs_by_user_body_and_path(rf):
    base = build_idempotency_key(1, _post(rf, BODY))
    assert base != build_idempotency_key(2, _post(rf, BODY))
    assert base != build_idempotency_key(1, _post(rf, {**BODY, "service_id": 4}))
    assert base != build_idempotency_key(1, _post(rf, BODY, path="/api/v2/appointments"))


def test_idempotency_key_header_replaces_the_body(rf):
    first = build_idempotency_key(1, _post(rf, BODY, HTTP_IDEMPOTENCY_KEY="abc"))
    second = build_idempotency_key(1, _post(rf, {**BODY, "service_id": 9}, HTTP_IDEMPOTENCY_KEY="abc"))
    assert first == second


def test_invalid_json_body_still_produces_a_key(rf):
    assert len(build_idempotency_key(1, _post(rf, "not json"))) == 64
