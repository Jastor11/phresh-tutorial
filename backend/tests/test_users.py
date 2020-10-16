import pytest

from httpx import AsyncClient
from fastapi import FastAPI
from databases import Database
from app.db.repositories.users import UsersRepository

from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from app.models.user import UserCreate, UserInDB


pytestmark = pytest.mark.asyncio


class TestUserRoutes:
    async def test_routes_exist(self, app: FastAPI, client: AsyncClient) -> None:
        new_user = {"email": "test@email.io", "username": "test_username", "password": "testpassword"}
        res = await client.post(app.url_path_for("users:register-new-user"), json={"new_user": new_user})
        assert res.status_code != HTTP_404_NOT_FOUND


# ...other code


class TestUserRegistration:
    async def test_users_can_register_successfully(self, app: FastAPI, client: AsyncClient, db: Database,) -> None:
        user_repo = UsersRepository(db)
        new_user = {"email": "shakira@shakira.io", "username": "shakirashakira", "password": "chantaje"}

        # make sure user doesn't exist yet
        user_in_db = await user_repo.get_user_by_email(email=new_user["email"])
        assert user_in_db is None

        # send post request to create user and ensure it is successful
        res = await client.post(app.url_path_for("users:register-new-user"), json={"new_user": new_user})
        assert res.status_code == HTTP_201_CREATED

        # ensure that the user now exists in the db
        user_in_db = await user_repo.get_user_by_email(email=new_user["email"])
        assert user_in_db is not None
        assert user_in_db.email == new_user["email"]
        assert user_in_db.username == new_user["username"]

        # check that the user returned in the response is equal to the user in the database
        created_user = UserInDB(**res.json(), password="whatever", salt="123").dict(exclude={"password", "salt"})
        assert created_user == user_in_db.dict(exclude={"password", "salt"})

    @pytest.mark.parametrize(
        "attr, value, status_code",
        (
            ("email", "shakira@shakira.io", 400),
            ("username", "shakirashakira", 400),
            ("email", "invalid_email@one@two.io", 422),
            ("password", "short", 422),
            ("username", "shakira@#$%^<>", 422),
            ("username", "ab", 422),
        ),
    )
    async def test_user_registration_fails_when_credentials_are_taken(
        self, app: FastAPI, client: AsyncClient, db: Database, attr: str, value: str, status_code: int,
    ) -> None:
        new_user = {"email": "nottaken@email.io", "username": "not_taken_username", "password": "freepassword"}
        new_user[attr] = value

        res = await client.post(app.url_path_for("users:register-new-user"), json={"new_user": new_user})
        assert res.status_code == status_code
