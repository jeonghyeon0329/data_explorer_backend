from pydantic import BaseModel


class SignupRequest(BaseModel):
    username: str
    name: str = ""
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    uid: int
    token: str
    password: str
