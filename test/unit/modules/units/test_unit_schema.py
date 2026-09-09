import pytest
from pydantic import ValidationError

from src.modules.units.unit_schema import (
    CreateUnitRequest,
    UnitResponse,
    UpdateUnitRequest,
)
from test.factories import make_create_unit_request, make_unit_row


def test_create_unit_request_accepts_valid_data():
    result = make_create_unit_request()

    assert isinstance(result, CreateUnitRequest)


def test_create_unit_request_rejects_invalid_email():
    with pytest.raises(ValidationError):
        make_create_unit_request(email="invalid-email")


def test_create_unit_request_rejects_empty_name():
    with pytest.raises(ValidationError):
        make_create_unit_request(name="")


def test_create_unit_request_rejects_invalid_state():
    with pytest.raises(ValidationError):
        make_create_unit_request(state="Paraná")


def test_create_unit_request_accepts_valid_cnpj():
    result = make_create_unit_request(cnpj="12345678000195")

    assert result.cnpj == "12345678000195"


def test_create_unit_request_rejects_invalid_cnpj():
    with pytest.raises(ValidationError):
        make_create_unit_request(cnpj="12345678000019")


def test_update_unit_request_accepts_partial_payload():
    result = UpdateUnitRequest(name="Unidade Nova")

    assert result.name == "Unidade Nova"
    assert result.cnpj is None
    assert result.email is None


def test_update_unit_request_accepts_valid_cnpj():
    result = UpdateUnitRequest(cnpj="12345678000195")

    assert result.cnpj == "12345678000195"


def test_update_unit_request_rejects_invalid_cnpj():
    with pytest.raises(ValidationError):
        UpdateUnitRequest(cnpj="12345678000019")


def test_unit_response_accepts_repository_data():
    row = make_unit_row()

    result = UnitResponse.model_validate(
        {
            **row,
            "is_active": row["isActive"],
            "created_at": row["createdAt"],
            "updated_at": row["updatedAt"],
        }
    )

    assert result.name == "Unidade Principal"
    assert result.is_active is True
