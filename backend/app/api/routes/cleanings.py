from typing import List

from fastapi import APIRouter, Body, Depends, status

from app.models.user import UserInDB
from app.models.cleaning import CleaningCreate, CleaningUpdate, CleaningInDB, CleaningPublic

from app.db.repositories.cleanings import CleaningsRepository

from app.api.dependencies.database import get_repository
from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.cleanings import get_cleaning_by_id_from_path, check_cleaning_modification_permissions


router = APIRouter()


@router.post("/", response_model=CleaningPublic, name="cleanings:create-cleaning", status_code=status.HTTP_201_CREATED)
async def create_new_cleaning(
    new_cleaning: CleaningCreate = Body(..., embed=True),
    current_user: UserInDB = Depends(get_current_active_user),
    cleanings_repo: CleaningsRepository = Depends(get_repository(CleaningsRepository)),
) -> CleaningPublic:
    return await cleanings_repo.create_cleaning(new_cleaning=new_cleaning, requesting_user=current_user)


@router.get("/", response_model=List[CleaningPublic], name="cleanings:list-all-user-cleanings")
async def list_all_user_cleanings(
    current_user: UserInDB = Depends(get_current_active_user),
    cleanings_repo: CleaningsRepository = Depends(get_repository(CleaningsRepository)),
) -> List[CleaningPublic]:
    return await cleanings_repo.list_all_user_cleanings(requesting_user=current_user)


@router.get("/{cleaning_id}/", response_model=CleaningPublic, name="cleanings:get-cleaning-by-id")
async def get_cleaning_by_id(cleaning: CleaningInDB = Depends(get_cleaning_by_id_from_path)) -> CleaningPublic:
    return cleaning


@router.put(
    "/{cleaning_id}/",
    response_model=CleaningPublic,
    name="cleanings:update-cleaning-by-id",
    dependencies=[Depends(check_cleaning_modification_permissions)],
)
async def update_cleaning_by_id(
    cleaning: CleaningInDB = Depends(get_cleaning_by_id_from_path),
    cleaning_update: CleaningUpdate = Body(..., embed=True),
    cleanings_repo: CleaningsRepository = Depends(get_repository(CleaningsRepository)),
) -> CleaningPublic:
    return await cleanings_repo.update_cleaning(cleaning=cleaning, cleaning_update=cleaning_update)


@router.delete(
    "/{cleaning_id}/",
    response_model=int,
    name="cleanings:delete-cleaning-by-id",
    dependencies=[Depends(check_cleaning_modification_permissions)],
)
async def delete_cleaning_by_id(
    cleaning: CleaningInDB = Depends(get_cleaning_by_id_from_path),
    cleanings_repo: CleaningsRepository = Depends(get_repository(CleaningsRepository)),
) -> int:
    return await cleanings_repo.delete_cleaning_by_id(cleaning=cleaning)
