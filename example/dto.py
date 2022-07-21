from pydantic import BaseModel, Field


class LoginModel(BaseModel):
    username: str
    password: str


class UserModel(BaseModel):
    id: int
    username: str


class QueryModel(BaseModel):
    page: int = Field(default=1, title="current page number")
    size: int = Field(default=20, title="size of page", ge=10, le=100)
    keyword: str = None
