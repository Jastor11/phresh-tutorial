from typing import List

from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST

from app.db.repositories.base import BaseRepository
from app.models.cleaning import CleaningCreate, CleaningUpdate, CleaningInDB


CREATE_CLEANING_QUERY = """
    INSERT INTO cleanings (name, description, price, cleaning_type)
    VALUES (:name, :description, :price, :cleaning_type)
    RETURNING id, name, description, price, cleaning_type;
"""

GET_CLEANING_BY_ID_QUERY = """
    SELECT id, name, description, price, cleaning_type
    FROM cleanings
    WHERE id = :id;
"""

GET_ALL_CLEANINGS_QUERY = """
    SELECT id, name, description, price, cleaning_type
    FROM cleanings;
"""

UPDATE_CLEANING_BY_ID_QUERY = """
    UPDATE cleanings
    SET name         = :name,
        description  = :description,
        price        = :price,
        cleaning_type = :cleaning_type
    WHERE id = :id
    RETURNING id, name, description, price, cleaning_type;
"""

DELETE_CLEANING_BY_ID_QUERY = """
    DELETE FROM cleanings
    WHERE id = :id
    RETURNING id;
"""


class CleaningsRepository(BaseRepository):
    """"
    All database actions associated with the Cleaning resource
    """

    async def create_cleaning(self, *, new_cleaning: CleaningCreate) -> CleaningInDB:
        query_values = new_cleaning.dict()
        cleaning = await self.db.fetch_one(query=CREATE_CLEANING_QUERY, values=query_values)

        return CleaningInDB(**cleaning)

    async def get_cleaning_by_id(self, *, id: int) -> CleaningInDB:
        cleaning = await self.db.fetch_one(query=GET_CLEANING_BY_ID_QUERY, values={"id": id})

        if not cleaning:
            return None

        return CleaningInDB(**cleaning)

    async def get_all_cleanings(self) -> List[CleaningInDB]:
        cleaning_records = await self.db.fetch_all(query=GET_ALL_CLEANINGS_QUERY)

        return [CleaningInDB(**l) for l in cleaning_records]

    async def update_cleaning(self, *, id: int, cleaning_update: CleaningUpdate) -> CleaningInDB:
        cleaning = await self.get_cleaning_by_id(id=id)

        if not cleaning:
            return None

        cleaning_update_params = cleaning.copy(update=cleaning_update.dict(exclude_unset=True))
        if cleaning_update_params.cleaning_type is None:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid cleaning type. Cannot be None.")

        try:
            updated_cleaning = await self.db.fetch_one(
                query=UPDATE_CLEANING_BY_ID_QUERY, values=cleaning_update_params.dict()
            )
            return CleaningInDB(**updated_cleaning)
        except Exception as e:
            print(e)
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid update params.")

    async def delete_cleaning_by_id(self, *, id: int) -> int:
        cleaning = await self.get_cleaning_by_id(id=id)

        if not cleaning:
            return None

        deleted_id = await self.db.execute(query=DELETE_CLEANING_BY_ID_QUERY, values={"id": id})

        return deleted_id
