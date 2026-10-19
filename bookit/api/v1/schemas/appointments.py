"""Pydantic schemas for the appointment endpoints."""
from decimal import Decimal

from pydantic import Field, model_validator

from bookit.api.common.pagination import PageParams
from bookit.api.common.schema_types import CaseInsensitiveStatus, UnixTimestamp
from bookit.api.common.schemas import RequestSchema, ResponseSchema
from bookit.models import Appointment, AppointmentStatus


class AppointmentCreateRequest(RequestSchema):
    """Body of POST /appointments."""

    service_id: int = Field(gt=0)
    start_time: UnixTimestamp


class AppointmentListQuery(PageParams):
    """Query parameters of GET /appointments (`from`/`to` are inclusive unix seconds)."""

    start_from: UnixTimestamp | None = Field(default=None, alias="from")
    start_to: UnixTimestamp | None = Field(default=None, alias="to")
    status: CaseInsensitiveStatus | None = None

    @model_validator(mode="after")
    def range_is_ordered(self) -> "AppointmentListQuery":
        """Reject a range whose start is after its end."""
        if self.start_from and self.start_to and self.start_from > self.start_to:
            raise ValueError("'from' must be less than or equal to 'to'")
        return self


class AppointmentOut(ResponseSchema):
    """One appointment with service, business and client display fields."""

    id: int
    status: AppointmentStatus
    start_time: UnixTimestamp
    end_time: UnixTimestamp
    service_id: int
    service_name: str
    price: Decimal
    business_id: int
    business_name: str
    client_id: int
    client_name: str

    @classmethod
    def from_model(cls, appointment: Appointment) -> "AppointmentOut":
        """Build the response; expects service, business and client to be preloaded."""
        service = appointment.service
        return cls(
            id=appointment.id,
            status=appointment.status,
            start_time=appointment.start_time,
            end_time=appointment.end_time,
            service_id=service.id,
            service_name=service.name,
            price=service.price,
            business_id=service.business_id,
            business_name=service.business.name,
            client_id=appointment.client_id,
            client_name=appointment.client.full_name,
        )
