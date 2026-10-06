import pytest
from pydantic import ValidationError

from src.modules.units.unit_schema import (
    CreateUnitRequest,
    UnitResponse,
    UpdateUnitRequest,
)
from test.factories import make_create_unit_request, make_unit_row

ALPHANUMERIC_CNPJ = "12ABC34501DE35"
MASKED_ALPHANUMERIC_CNPJ = "12.ABC.345/01DE-35"


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


def test_create_unit_request_accepts_valid_alphanumeric_cnpj():
    result = make_create_unit_request(cnpj=ALPHANUMERIC_CNPJ)

    assert result.cnpj == ALPHANUMERIC_CNPJ


def test_create_and_update_schemas_document_alphanumeric_cnpj_example():
    create_examples = CreateUnitRequest.model_json_schema()["properties"]["cnpj"]["examples"]
    update_examples = UpdateUnitRequest.model_json_schema()["properties"]["cnpj"]["examples"]

    assert ALPHANUMERIC_CNPJ in create_examples
    assert ALPHANUMERIC_CNPJ in update_examples


def test_create_unit_request_normalizes_masked_lowercase_cnpj():
    result = make_create_unit_request(cnpj=MASKED_ALPHANUMERIC_CNPJ.lower())

    assert result.cnpj == ALPHANUMERIC_CNPJ


@pytest.mark.parametrize(
    "cnpj",
    ["12-ABC.345/01DE-35", "12ABC34501DE3A", "12ABC34501DE36"],
)
def test_create_unit_request_rejects_invalid_alphanumeric_cnpj(cnpj):
    with pytest.raises(ValidationError):
        make_create_unit_request(cnpj=cnpj)


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


def test_update_unit_request_normalizes_masked_alphanumeric_cnpj():
    result = UpdateUnitRequest(cnpj=MASKED_ALPHANUMERIC_CNPJ)

    assert result.cnpj == ALPHANUMERIC_CNPJ


def test_update_unit_request_rejects_invalid_alphanumeric_cnpj_checksum():
    with pytest.raises(ValidationError):
        UpdateUnitRequest(cnpj="12ABC34501DE36")


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
