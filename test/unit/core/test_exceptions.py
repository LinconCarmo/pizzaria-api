from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from src.core.exceptions import (
    BusinessValidationError,
    ConflictError,
    DomainError,
    NotFoundError,
    UnauthorizedError,
    domain_error_handler,
    generic_exception_handler,
    validation_exception_handler,
)


# ---------------------------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------------------------


def test_not_found_error_has_correct_code_and_status():
    err = NotFoundError("item missing")

    assert err.code == "NOT_FOUND"
    assert err.status_code == 404
    assert err.message == "item missing"


def test_conflict_error_has_correct_code_and_status():
    err = ConflictError("already exists")

    assert err.code == "CONFLICT"
    assert err.status_code == 409


def test_business_validation_error_has_correct_code_and_status():
    err = BusinessValidationError("bad input", details=["field required"])

    assert err.code == "VALIDATION_ERROR"
    assert err.status_code == 422
    assert err.details == ["field required"]


def test_unauthorized_error_has_correct_code_and_status():
    err = UnauthorizedError()

    assert err.code == "UNAUTHORIZED"
    assert err.status_code == 401


def test_domain_error_is_base_for_all_subclasses():
    assert issubclass(NotFoundError, DomainError)
    assert issubclass(ConflictError, DomainError)
    assert issubclass(BusinessValidationError, DomainError)
    assert issubclass(UnauthorizedError, DomainError)


# ---------------------------------------------------------------------------
# domain_error_handler
# ---------------------------------------------------------------------------


def _app_with_domain_handler() -> tuple[FastAPI, TestClient]:
    app = FastAPI()
    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
    return app, TestClient(app, raise_server_exceptions=False)


def test_domain_error_handler_returns_correct_payload_for_not_found():
    app, client = _app_with_domain_handler()

    @app.get("/not-found")
    async def _():
        raise NotFoundError("User 1 not found")

    resp = client.get("/not-found")

    assert resp.status_code == 404
    assert resp.json() == {
        "error": {"code": "NOT_FOUND", "message": "User 1 not found", "details": None}
    }


def test_domain_error_handler_returns_correct_payload_for_conflict():
    app, client = _app_with_domain_handler()

    @app.get("/conflict")
    async def _():
        raise ConflictError("duplicate email")

    resp = client.get("/conflict")

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


def test_domain_error_handler_returns_correct_payload_for_unauthorized():
    app, client = _app_with_domain_handler()

    @app.get("/auth")
    async def _():
        raise UnauthorizedError()

    resp = client.get("/auth")

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# validation_exception_handler
# ---------------------------------------------------------------------------


def test_validation_exception_handler_returns_422_with_details():
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    client = TestClient(app, raise_server_exceptions=False)

    @app.get("/validated")
    async def _(q: int):
        return {"q": q}

    resp = client.get("/validated?q=not_an_int")

    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Validation failed"
    assert isinstance(body["error"]["details"], list)
    assert len(body["error"]["details"]) > 0


# ---------------------------------------------------------------------------
# generic_exception_handler
# ---------------------------------------------------------------------------


def test_generic_exception_handler_returns_500_and_logs_exception():
    app = FastAPI()
    app.add_exception_handler(Exception, generic_exception_handler)
    client = TestClient(app, raise_server_exceptions=False)

    @app.get("/boom")
    async def _():
        raise RuntimeError("unexpected")

    with patch("src.core.exceptions.logger") as mock_logger:
        resp = client.get("/boom")

    assert resp.status_code == 500
    assert resp.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
            "details": None,
        }
    }
    mock_logger.exception.assert_called_once()
