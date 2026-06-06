import logging

from app import observability


def test_known_event_logs_without_warning(caplog):
    with caplog.at_level(logging.INFO, logger="events"):
        observability.emit("project_created", project_id="p1")
    assert any("project_created" in r.message for r in caplog.records)
    assert not any(r.levelno >= logging.WARNING for r in caplog.records)


def test_unknown_event_warns(caplog):
    with caplog.at_level(logging.WARNING, logger="events"):
        observability.emit("not_a_real_event", x=1)
    assert any(r.levelno >= logging.WARNING for r in caplog.records)
