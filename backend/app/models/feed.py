from typing import Optional, Literal
import datetime

from app.models.core import CoreModel
from app.models.cleaning import CleaningPublic


class FeedItem(CoreModel):
    row_number: Optional[int]
    event_timestamp: Optional[datetime.datetime]


class CleaningFeedItem(CleaningPublic, FeedItem):
    event_type: Optional[Literal["is_update", "is_create"]]

