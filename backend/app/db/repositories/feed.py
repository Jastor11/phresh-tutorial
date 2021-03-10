from typing import List
import datetime

from databases import Database
from asyncpg import Record

from app.db.repositories.base import BaseRepository
from app.db.repositories.users import UsersRepository

# from app.models.user import UserInDB
from app.models.feed import CleaningFeedItem


FETCH_CLEANING_JOBS_FOR_FEED_QUERY = """
    SELECT id,
           name,
           description,
           price,
           cleaning_type,
           owner,
           created_at,
           updated_at,
           event_type,
           event_timestamp,
           ROW_NUMBER() OVER ( ORDER BY event_timestamp DESC ) AS row_number
    FROM (
        (
            SELECT id,
                   name,
                   description,
                   price,
                   cleaning_type,
                   owner,
                   created_at,
                   updated_at,
                   updated_at AS event_timestamp,
                   'is_update' AS event_type
            FROM cleanings
            WHERE updated_at < :starting_date AND updated_at != created_at
            ORDER BY updated_at DESC
            LIMIT :page_chunk_size
        ) UNION (
            SELECT id,
                   name,
                   description,
                   price,
                   cleaning_type,
                   owner,
                   created_at,
                   updated_at,
                   created_at AS event_timestamp,
                   'is_create' AS event_type
            FROM cleanings
            WHERE created_at < :starting_date
            ORDER BY created_at DESC
            LIMIT :page_chunk_size
        )
    ) AS cleaning_feed
    ORDER BY event_timestamp DESC
    LIMIT :page_chunk_size;
"""


class FeedRepository(BaseRepository):
    def __init__(self, db: Database) -> None:
        super().__init__(db)
        self.users_repo = UsersRepository(db)

    async def fetch_cleaning_jobs_feed(
        self, *, starting_date: datetime.datetime, page_chunk_size: int = 20
    ) -> List[CleaningFeedItem]:
        cleaning_feed_item_records = await self.db.fetch_all(
            query=FETCH_CLEANING_JOBS_FOR_FEED_QUERY,
            values={"starting_date": starting_date, "page_chunk_size": page_chunk_size},
        )

        return [
            await self.populate_cleaning_feed_item(cleaning_feed_item=cleaning_feed_item)
            for cleaning_feed_item in cleaning_feed_item_records
        ]

    async def populate_cleaning_feed_item(self, *, cleaning_feed_item: Record) -> CleaningFeedItem:
        return CleaningFeedItem(
            **{k: v for k, v in cleaning_feed_item.items() if k != "owner"},
            owner=await self.users_repo.get_user_by_id(user_id=cleaning_feed_item["owner"])
        )

