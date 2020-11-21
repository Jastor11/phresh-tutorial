from typing import List

from fastapi import HTTPException, status
from asyncpg.exceptions import UniqueViolationError

from app.db.repositories.base import BaseRepository
from app.models.cleaning import CleaningInDB
from app.models.user import UserInDB
from app.models.offer import OfferCreate, OfferUpdate, OfferInDB


CREATE_OFFER_FOR_CLEANING_QUERY = """
    INSERT INTO user_offers_for_cleanings (cleaning_id, user_id, status)
    VALUES (:cleaning_id, :user_id, :status)
    RETURNING cleaning_id, user_id, status, created_at, updated_at;
"""

LIST_OFFERS_FOR_CLEANING_QUERY = """
    SELECT cleaning_id, user_id, status, created_at, updated_at
    FROM user_offers_for_cleanings
    WHERE cleaning_id = :cleaning_id;
"""

GET_OFFER_FOR_CLEANING_FROM_USER_QUERY = """
    SELECT cleaning_id, user_id, status, created_at, updated_at
    FROM user_offers_for_cleanings
    WHERE cleaning_id = :cleaning_id AND user_id = :user_id;
"""

ACCEPT_OFFER_QUERY = """
    UPDATE user_offers_for_cleanings
    SET status = 'accepted'
    WHERE cleaning_id = :cleaning_id AND user_id = :user_id
    RETURNING cleaning_id, user_id, status, created_at, updated_at;
"""

REJECT_ALL_OTHER_OFFERS_QUERY = """
    UPDATE user_offers_for_cleanings
    SET status = 'rejected'
    WHERE cleaning_id = :cleaning_id
    AND user_id != :user_id
    AND status = 'pending';
"""

CANCEL_OFFER_QUERY = """
    UPDATE user_offers_for_cleanings
    SET status = 'cancelled'
    WHERE cleaning_id = :cleaning_id AND user_id = :user_id
    RETURNING cleaning_id, user_id, status, created_at, updated_at;
"""

SET_ALL_OTHER_OFFERS_AS_PENDING_QUERY = """
    UPDATE user_offers_for_cleanings
    SET status = 'pending'
    WHERE cleaning_id = :cleaning_id
    AND user_id != :user_id
    AND status = 'rejected';
"""

RESCIND_OFFER_QUERY = """
    DELETE FROM user_offers_for_cleanings
    WHERE cleaning_id = :cleaning_id
    AND user_id = :user_id;
"""

MARK_OFFER_COMPLETED_QUERY = """
    UPDATE user_offers_for_cleanings
    SET status = 'completed'
    WHERE cleaning_id = :cleaning_id AND user_id = :user_id;
"""


class OffersRepository(BaseRepository):
    async def create_offer_for_cleaning(self, *, new_offer: OfferCreate) -> OfferInDB:
        created_offer = await self.db.fetch_one(
            query=CREATE_OFFER_FOR_CLEANING_QUERY, values={**new_offer.dict(), "status": "pending"},
        )
        return OfferInDB(**created_offer)

    async def list_offers_for_cleaning(self, *, cleaning: CleaningInDB) -> List[OfferInDB]:
        offers = await self.db.fetch_all(query=LIST_OFFERS_FOR_CLEANING_QUERY, values={"cleaning_id": cleaning.id})

        return [OfferInDB(**o) for o in offers]

    async def get_offer_for_cleaning_from_user(self, *, cleaning: CleaningInDB, user: UserInDB) -> OfferInDB:
        offer_record = await self.db.fetch_one(
            query=GET_OFFER_FOR_CLEANING_FROM_USER_QUERY, values={"cleaning_id": cleaning.id, "user_id": user.id},
        )

        if not offer_record:
            return None

        return OfferInDB(**offer_record)

    async def accept_offer(self, *, offer: OfferInDB, offer_update: OfferUpdate) -> OfferInDB:
        async with self.db.transaction():
            accepted_offer = await self.db.fetch_one(
                query=ACCEPT_OFFER_QUERY,  # accept current offer
                values={"cleaning_id": offer.cleaning_id, "user_id": offer.user_id},
            )

            await self.db.execute(
                query=REJECT_ALL_OTHER_OFFERS_QUERY,  # reject all other offers
                values={"cleaning_id": offer.cleaning_id, "user_id": offer.user_id},
            )

            return OfferInDB(**accepted_offer)

    async def cancel_offer(self, *, offer: OfferInDB, offer_update: OfferUpdate) -> OfferInDB:
        async with self.db.transaction():
            cancelled_offer = await self.db.fetch_one(
                query=CANCEL_OFFER_QUERY,  # cancel current offer
                values={"cleaning_id": offer.cleaning_id, "user_id": offer.user_id},
            )

            await self.db.execute(
                query=SET_ALL_OTHER_OFFERS_AS_PENDING_QUERY,  # set all other offers to pending again
                values={"cleaning_id": offer.cleaning_id, "user_id": offer.user_id},
            )

            return OfferInDB(**cancelled_offer)

    async def rescind_offer(self, *, offer: OfferInDB) -> int:
        return await self.db.execute(
            query=RESCIND_OFFER_QUERY,  # rescinding an offer deletes it as long as it's pending
            values={"cleaning_id": offer.cleaning_id, "user_id": offer.user_id},
        )

    async def mark_offer_completed(self, *, cleaning: CleaningInDB, cleaner: UserInDB) -> OfferInDB:
        return await self.db.fetch_one(
            query=MARK_OFFER_COMPLETED_QUERY,  # owner of cleaning marks job status as completed
            values={"cleaning_id": cleaning.id, "user_id": cleaner.id},
        )
