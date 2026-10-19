"""Appointment endpoints."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bookit.api.common.idempotency import idempotent
from bookit.api.common.pagination import paginate
from bookit.api.common.parsing import parse_body, parse_query

from ..dependencies import get_appointment_service
from ..schemas.appointments import AppointmentCreateRequest, AppointmentListQuery, AppointmentOut


class AppointmentListCreateView(APIView):
    """GET/POST /appointments: list the caller's appointments or book a new one."""

    def get(self, request):
        """Return one page of the caller's appointments, filtered by time range and status."""
        query = parse_query(AppointmentListQuery, request)
        appointments = get_appointment_service().list_for_user(
            user=request.user, start_from=query.start_from, start_to=query.start_to, status=query.status
        )
        return Response(paginate(appointments, query, request, AppointmentOut).model_dump(mode="json"))

    @idempotent
    def post(self, request):
        """Book an appointment for the calling client."""
        payload = parse_body(AppointmentCreateRequest, request)
        appointment = get_appointment_service().book(
            client=request.user, service_id=payload.service_id, start_time=payload.start_time
        )
        return Response(AppointmentOut.from_model(appointment).model_dump(mode="json"), status=status.HTTP_201_CREATED)
