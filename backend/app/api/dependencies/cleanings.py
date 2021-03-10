from fastapi import HTTPException, Depends, Path, status

from app.models.user import UserInDB
from app.models.cleaning import CleaningPublic
from app.db.repositories.cleanings import CleaningsRepository

from app.api.dependencies.database import get_repository
from app.api.dependencies.auth import get_current_active_user


async def get_cleaning_by_id_from_path(
    cleaning_id: int = Path(..., ge=1),
    current_user: UserInDB = Depends(get_current_active_user),
    cleanings_repo: CleaningsRepository = Depends(get_repository(CleaningsRepository)),
) -> CleaningPublic:
    cleaning = await cleanings_repo.get_cleaning_by_id(id=cleaning_id, requesting_user=current_user)

    if not cleaning:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No cleaning found with that id.",
        )

    return cleaning


def check_cleaning_modification_permissions(
    current_user: UserInDB = Depends(get_current_active_user),
    cleaning: CleaningPublic = Depends(get_cleaning_by_id_from_path),
) -> None:
    if not user_owns_cleaning(user=current_user, cleaning=cleaning):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Users are only able to modify cleanings that they created.",
        )


def user_owns_cleaning(*, user: UserInDB, cleaning: CleaningPublic) -> bool:
    if isinstance(cleaning.owner, int):
        return cleaning.owner == user.id

    return cleaning.owner.id == user.id
