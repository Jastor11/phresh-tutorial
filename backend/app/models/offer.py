from typing import Optional, Union
from enum import Enum, auto

from pydantic import Field

from app.models.core import DateTimeModelMixin, CoreModel
from app.models.user import UserPublic
from app.models.cleaning import CleaningPublic


class OfferStatus(str, Enum):
    accepted = "accepted"
    rejected = "rejected"
    pending = "pending"
    cancelled = "cancelled"


class OfferBase(CoreModel):
    user_id: Optional[int]
    cleaning_id: Optional[int]
    status: Optional[OfferStatus] = OfferStatus.pending


class OfferCreate(OfferBase):
    user_id: int
    cleaning_id: int


class OfferUpdate(CoreModel):
    status: OfferStatus


class OfferInDB(DateTimeModelMixin, OfferBase):
    pass


class OfferPublic(OfferInDB):
    user: Union[int, UserPublic] = Field(..., alias="user_id")
    cleaning: Union[int, CleaningPublic] = Field(..., alias="cleaning_id")

    class Config:
        allow_population_by_field_name = True
