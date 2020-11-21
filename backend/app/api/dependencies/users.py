from fastapi import HTTPException, Depends, Path, status

from app.models.user import UserInDB
from app.db.repositories.users import UsersRepository

from app.api.dependencies.database import get_repository
from app.api.dependencies.auth import get_current_active_user


async def get_user_by_username_from_path(
    username: str = Path(..., min_length=3, regex="^[a-zA-Z0-9_-]+$"),
    current_user: UserInDB = Depends(get_current_active_user),
    users_repo: UsersRepository = Depends(get_repository(UsersRepository)),
) -> UserInDB:
    user = await users_repo.get_user_by_username(username=username, populate=False)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No user found with that username.",
        )

    return user
