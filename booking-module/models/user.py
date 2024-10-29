from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from bson import ObjectId
from enum import Enum


# Helper class for handling MongoDB ObjectID in Pydantic
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid object id")
        return ObjectId(v)


class AccountStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Insurance(BaseModel):
    group_id: str
    member_id: str
    insurance_company_name: str


class Address(BaseModel):
    street_address: str
    apartment_unit: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = Field(default="United States of America")


class FullName(BaseModel):
    first: str
    last: str


class User(BaseModel):
    name: FullName
    email: EmailStr
    date_of_birth: datetime
    hashed_password: str
    appointments: Optional[List[PyObjectId]] = []
    account_status: AccountStatus = Field(default=AccountStatus.ACTIVE)
    insurance: Insurance
    address: Address

    def full_name(self) -> str:
        return f"{self.name['first']} {self.name['last']}"

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
