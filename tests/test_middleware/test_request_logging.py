import logging

from django.http import HttpResponse

from bookit.middleware.request_logging import RequestLoggingMiddleware


def test_logs_method_path_status_and_duration(rf, caplog):
    middleware = RequestLoggingMiddleware(lambda request: HttpResponse(status=201))
    with caplog.at_level(logging.INFO, logger="bookit.requests"):
        middleware(rf.post("/api/v1/appointments?x=1"))
    record = next(r for r in caplog.records if r.name == "bookit.requests")
    assert (record.method, record.path, record.status_code) == ("POST", "/api/v1/appointments", 201)
    assert record.duration_ms >= 0
    assert "POST /api/v1/appointments -> 201" in record.getMessage()
