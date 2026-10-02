from datetime import UTC, datetime
from uuid import UUID

from src.modules.units.unit_schema import (
    CreateUnitRequest,
)

NOW = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)
DEFAULT_UNIT_ID = UUID("00000000-0000-4000-8000-000000000002")


def make_unit_row(
    *,
    id: UUID = DEFAULT_UNIT_ID,
    name: str = "Unidade Principal",
    cnpj: str = "12345678000195",
    email: str = "lincon_unit@pizzaria.com",
    phone: str = "41999999999",
    street: str = "Rua Antonio Batista Prado",
    number: str = "23",
    neighborhood: str = "Jardim Menino Deus",
    city: str = "Quatro Barras",
    state: str = "PR",
    zip: str = "83422-230",
    is_active: bool = True,
    created_at: datetime = NOW,
    updated_at: datetime = NOW,
    deleted_at: datetime | None = None,
) -> dict[str, object]:

    return {
        "id": str(id),
        "name": name,
        "cnpj": cnpj,
        "email": email,
        "phone": phone,
        "street": street,
        "number": number,
        "neighborhood": neighborhood,
        "city": city,
        "state": state,
        "zip": zip,
        "isActive": is_active,
        "createdAt": created_at,
        "updatedAt": updated_at,
        "deletedAt": deleted_at,
    }


def make_create_unit_request(
    *,
    name: str = "Unidade Principal",
    cnpj: str = "12345678000195",
    email: str = "lincon_unit@pizzaria.com",
    phone: str = "41999999999",
    street: str = "Rua Antonio Batista Prado",
    number: str = "23",
    neighborhood: str = "Jardim Menino Deus",
    city: str = "Quatro Barras",
    state: str = "PR",
    zip: str = "83422-230",
) -> CreateUnitRequest:
    return CreateUnitRequest(
        name=name,
        cnpj=cnpj,
        email=email,
        phone=phone,
        street=street,
        number=number,
        neighborhood=neighborhood,
        city=city,
        state=state,
        zip=zip,
    )
