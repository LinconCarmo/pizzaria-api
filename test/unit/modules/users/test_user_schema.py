import pytest
from pydantic import ValidationError

from src.modules.users.user_schema import (
    CreateUserRequest,
    UserResponse,
    UserRole,
)
from test.factories import make_create_user_request, make_update_user_request

VALID_PAYLOAD = {
    "email": "ana@example.com",
    "name": "Ana",
    "password": "strongpass123",
}


def test_create_user_request_accepts_valid_payload():
    request = make_create_user_request()

    assert request.email == "ana@example.com"
    assert request.role == UserRole.CUSTOMER


def test_create_user_request_rejects_invalid_email():
    payload = {**VALID_PAYLOAD, "email": "not-an-email"}

    with pytest.raises(ValidationError):
        CreateUserRequest(**payload)


def test_create_user_request_rejects_password_shorter_than_8():
    payload = {**VALID_PAYLOAD, "password": "short"}

    with pytest.raises(ValidationError):
        CreateUserRequest(**payload)


def test_create_user_request_rejects_empty_name():
    payload = {**VALID_PAYLOAD, "name": ""}

    with pytest.raises(ValidationError):
        CreateUserRequest(**payload)


def test_create_user_request_defaults_role_to_customer():
    request = make_create_user_request()

    assert request.role == UserRole.CUSTOMER


def test_update_user_request_allows_all_fields_optional():
    request = make_update_user_request()

    assert request.model_dump(exclude_unset=True) == {}


def test_update_user_request_partial_payload_only_includes_provided_fields():
    request = make_update_user_request(name="New Name")

    dumped = request.model_dump(exclude_unset=True)

    assert dumped == {"name": "New Name"}


def test_user_response_does_not_expose_password_field():
    assert "password" not in UserResponse.model_fields
    assert "hashed_password" not in UserResponse.model_fields
    assert "hashedPassword" not in UserResponse.model_fields
