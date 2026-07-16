import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

_USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]+$")


def normalize_username(value: str) -> str:
    normalized = value.strip().casefold()
    if not _USERNAME_PATTERN.fullmatch(normalized):
        message = "Username may only contain letters, numbers, dots, underscores, and hyphens"
        raise ValueError(message)
    return normalized


def validate_password(value: str) -> str:
    if not value.strip():
        raise ValueError("Password cannot be empty or whitespace only")
    return value


class SetupRequest(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=64)]
    password: Annotated[str, Field(min_length=12, max_length=256)]

    @field_validator("username")
    @classmethod
    def normalize_setup_username(cls, value: str) -> str:
        return normalize_username(value)

    @field_validator("password")
    @classmethod
    def validate_setup_password(cls, value: str) -> str:
        return validate_password(value)


class LoginRequest(BaseModel):
    username: Annotated[str, Field(min_length=1, max_length=64)]
    password: Annotated[str, Field(min_length=1, max_length=256)]

    @field_validator("username")
    @classmethod
    def normalize_login_username(cls, value: str) -> str:
        return value.strip().casefold()


class PasswordChangeRequest(BaseModel):
    current_password: Annotated[str, Field(min_length=1, max_length=256)]
    new_password: Annotated[str, Field(min_length=12, max_length=256)]

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password(value)

    @model_validator(mode="after")
    def reject_reused_password(self) -> "PasswordChangeRequest":
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current password")
        return self


class AuthStatusResponse(BaseModel):
    setup_required: bool
    authenticated: bool
    username: str | None = None


class AuthUserResponse(BaseModel):
    username: str
    created_at: datetime


class SessionRevocationResponse(BaseModel):
    revoked_sessions: int
