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

