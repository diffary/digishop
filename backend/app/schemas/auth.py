from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_password_byte_length(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("password must be at most 72 bytes")
    return password


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def _password_byte_length(cls, value: str) -> str:
        return _validate_password_byte_length(value)


class LoginIn(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def _password_byte_length(cls, value: str) -> str:
        return _validate_password_byte_length(value)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
