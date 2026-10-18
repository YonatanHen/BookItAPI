import logging
import re

from django.http import HttpResponse

from bookit.middleware.correlation import HEADER, CorrelationIdFilter, CorrelationIdMiddleware, get_correlation_id

HEX32 = re.compile(r"[0-9a-f]{32}")


def _run(rf, **headers):
    seen = {}

    def view(request):
        seen["id"] = get_correlation_id()
        return HttpResponse()

    response = CorrelationIdMiddleware(view)(rf.get("/", **headers))
    return response, seen["id"]


def test_generates_an_id_when_none_is_sent(rf):
    response, inside_request = _run(rf)
    assert HEX32.fullmatch(response[HEADER])
    assert inside_request == response[HEADER]


def test_reuses_a_safe_incoming_id(rf):
    response, _ = _run(rf, HTTP_X_CORRELATION_ID="req-123.abc")
    assert response[HEADER] == "req-123.abc"


def test_replaces_an_unsafe_incoming_id(rf):
    response, _ = _run(rf, HTTP_X_CORRELATION_ID="bad id\nINJECTED")
    assert HEX32.fullmatch(response[HEADER])


def test_id_is_cleared_after_the_request(rf):
    _run(rf)
    assert get_correlation_id() == "-"


def test_log_filter_adds_the_current_id():
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "msg", None, None)
    assert CorrelationIdFilter().filter(record) is True
    assert record.correlation_id == "-"
