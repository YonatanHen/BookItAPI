import pytest
from pydantic import ValidationError

from bookit.api.v1.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, UserOut
from bookit.models import User, UserRole

VALID = {"email": "ok@bookit-test.io", "password": "Str0ng-Passw0rd!", "full_name": "Ok User", "role": "Client"}


def test_valid_register_request_parses_role_enum():
    payload = RegisterRequest.model_validate(VALID)
    assert payload.role is UserRole.CLIENT


@pytest.mark.parametrize(
    "override, field",
    [
        ({"email": "not-an-email"}, "email"),
        ({"password": "short"}, "password"),
        ({"password": "12345678901"}, "password"),
        ({"role": "Admin"}, "role"),
        ({"full_name": "   "}, "full_name"),
        ({"is_staff": True}, "is_staff"),
    ],
)
def test_invalid_register_requests_are_rejected(override, field):
    with pytest.raises(ValidationError) as caught:
        RegisterRequest.model_validate({**VALID, **override})
    assert field in [str(error["loc"][0]) for error in caught.value.errors()]


def test_login_and_refresh_require_their_fields():
    with pytest.raises(ValidationError):
        LoginRequest.model_validate({"email": "ok@bookit-test.io"})
    with pytest.raises(ValidationError):
        RefreshRequest.model_validate({"refresh": ""})


def test_user_out_never_contains_the_password():
    user = User(id=7, email="ok@bookit-test.io", full_name="Ok", role=UserRole.BUSINESS_OWNER, password="hash")
    assert UserOut.from_model(user).model_dump(mode="json") == {
        "id": 7,
        "email": "ok@bookit-test.io",
        "full_name": "Ok",
        "role": "BusinessOwner",
    }
