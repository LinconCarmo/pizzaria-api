from collections.abc import Iterator
from typing import (
    Any,  # noqa: TID251 -- registros de log capturados são dicts dinâmicos navegados nas asserções
)

import pytest

from src.core.logger import REDACTED, logger, request_id_var

RECORD_LIST_KEY = "records"


@pytest.fixture
def captured_records() -> Iterator[list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []

    def sink(message: Any) -> None:
        records.append(dict(message.record))

    handler_id = logger.add(sink, level="DEBUG", format="{message}")
    try:
        yield records
    finally:
        logger.remove(handler_id)


class TestRedactPatcher:
    def test_redacts_password_in_extra(self, captured_records: list[dict[str, Any]]) -> None:
        logger.bind(password="my-secret-pw").info("login_attempt")

        assert captured_records[0]["extra"]["password"] == REDACTED

    def test_redacts_token_authorization_and_api_key(
        self, captured_records: list[dict[str, Any]]
    ) -> None:
        logger.bind(
            token="t",
            access_token="a",
            refresh_token="r",
            authorization="Bearer x",
            api_key="k",
            secret="s",
        ).info("creds")

        extra = captured_records[0]["extra"]
        for key in ("token", "access_token", "refresh_token", "authorization", "api_key", "secret"):
            assert extra[key] == REDACTED

    def test_redacts_br_documents(self, captured_records: list[dict[str, Any]]) -> None:
        logger.bind(cpf="123.456.789-00", cnpj="00.000.000/0001-00", rg="12.345.678-9").info("docs")

        extra = captured_records[0]["extra"]
        assert extra["cpf"] == REDACTED
        assert extra["cnpj"] == REDACTED
        assert extra["rg"] == REDACTED

    def test_redacts_payment_fields(self, captured_records: list[dict[str, Any]]) -> None:
        logger.bind(
            card="4111",
            card_number="4111111111111111",
            cvv="123",
            ccv="123",
            pan="x",
        ).info("payment")

        extra = captured_records[0]["extra"]
        for key in ("card", "card_number", "cvv", "ccv", "pan"):
            assert extra[key] == REDACTED

    def test_redacts_contact_pii(self, captured_records: list[dict[str, Any]]) -> None:
        logger.bind(
            email="user@example.com",
            phone="+55 11 9 0000-0000",
            telefone="119...",
            address="Rua X, 1",
            endereco="Rua X, 1",
        ).info("contact")

        extra = captured_records[0]["extra"]
        for key in ("email", "phone", "telefone", "address", "endereco"):
            assert extra[key] == REDACTED

    def test_redacts_nested_dict(self, captured_records: list[dict[str, Any]]) -> None:
        payload = {"user": {"id": 1, "password": "x", "profile": {"cpf": "111"}}}

        logger.bind(payload=payload).info("nested")

        extra = captured_records[0]["extra"]
        assert extra["payload"]["user"]["password"] == REDACTED
        assert extra["payload"]["user"]["profile"]["cpf"] == REDACTED
        assert extra["payload"]["user"]["id"] == 1

    def test_redacts_inside_list(self, captured_records: list[dict[str, Any]]) -> None:
        logger.bind(users=[{"id": 1, "token": "a"}, {"id": 2, "token": "b"}]).info("list")

        extra = captured_records[0]["extra"]
        assert extra["users"][0]["token"] == REDACTED
        assert extra["users"][1]["token"] == REDACTED
        assert extra["users"][0]["id"] == 1

    def test_preserves_safe_keys(self, captured_records: list[dict[str, Any]]) -> None:
        logger.bind(user_id=42, order_id=7, status="paid").info("order_event")

        extra = captured_records[0]["extra"]
        assert extra["user_id"] == 42
        assert extra["order_id"] == 7
        assert extra["status"] == "paid"

    def test_redaction_is_case_insensitive(self, captured_records: list[dict[str, Any]]) -> None:
        logger.bind(Authorization="Bearer x", CPF="111", Email="a@b.c").info("case")

        extra = captured_records[0]["extra"]
        assert extra["Authorization"] == REDACTED
        assert extra["CPF"] == REDACTED
        assert extra["Email"] == REDACTED


class TestCorrelationId:
    def test_request_id_injected_into_extra_when_set(
        self, captured_records: list[dict[str, Any]]
    ) -> None:
        token = request_id_var.set("abc-123")
        try:
            logger.info("inside_request")
        finally:
            request_id_var.reset(token)

        assert captured_records[0]["extra"]["request_id"] == "abc-123"

    def test_request_id_absent_when_not_set(self, captured_records: list[dict[str, Any]]) -> None:
        logger.info("outside_request")

        assert "request_id" not in captured_records[0]["extra"]

    def test_explicit_request_id_in_bind_is_preserved(
        self, captured_records: list[dict[str, Any]]
    ) -> None:
        token = request_id_var.set("from-contextvar")
        try:
            logger.bind(request_id="explicit-bind").info("override")
        finally:
            request_id_var.reset(token)

        assert captured_records[0]["extra"]["request_id"] == "explicit-bind"
