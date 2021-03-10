from typing import Optional
from enum import Enum

from app.models.core import DateTimeModelMixin, CoreModel
from app.models.user import UserPublic
from app.models.cleaning import CleaningPublic


class OfferStatus(str, Enum):
    accepted = "accepted"
    rejected = "rejected"
    pending = "pending"
    cancelled = "cancelled"
    completed = "completed"


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
    user_id: int
    cleaning_id: int


class OfferPublic(OfferInDB):
    user: Optional[UserPublic]
    cleaning: Optional[CleaningPublic]
