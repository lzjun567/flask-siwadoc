from typing import Optional

from pydantic import BaseModel, AnyUrl, EmailStr


class Contact(BaseModel):
    name: Optional[str] = None
    url: Optional[AnyUrl] = None
    email: Optional[EmailStr] = None

    class Config:
        extra = "allow"


class License(BaseModel):
    name: str
    url: Optional[AnyUrl] = None

    class Config:
        extra = "allow"


class Info(BaseModel):
    title: str
    description: Optional[str] = None
    termsOfService: Optional[str] = None
    contact: Optional[Contact] = None
    license: Optional[License] = None
    version: str

    class Config:
        extra = "allow"
