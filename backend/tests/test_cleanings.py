from typing import List, Union

import pytest

from httpx import AsyncClient
from fastapi import FastAPI


from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY

from app.models.cleaning import CleaningCreate, CleaningInDB

# decorate all tests with @pytest.mark.asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def new_cleaning():
    return CleaningCreate(name="test cleaning", description="test description", price=0.00, cleaning_type="spot_clean",)


class TestCleaningsRoutes:
    async def test_routes_exist(self, app: FastAPI, client: AsyncClient) -> None:
        res = await client.post(app.url_path_for("cleanings:create-cleaning"), json={})
        assert res.status_code != HTTP_404_NOT_FOUND

    async def test_invalid_input_raises_error(self, app: FastAPI, client: AsyncClient) -> None:
        res = await client.post(app.url_path_for("cleanings:create-cleaning"), json={})
        assert res.status_code == HTTP_422_UNPROCESSABLE_ENTITY


class TestCreateCleaning:
    async def test_valid_input_creates_cleaning(
        self, app: FastAPI, client: AsyncClient, new_cleaning: CleaningCreate
    ) -> None:
        res = await client.post(
            app.url_path_for("cleanings:create-cleaning"), json={"new_cleaning": new_cleaning.dict()}
        )
        assert res.status_code == HTTP_201_CREATED

        created_cleaning = CleaningCreate(**res.json())
        assert created_cleaning == new_cleaning

    @pytest.mark.parametrize(
        "invalid_payload, status_code",
        (
            (None, 422),
            ({}, 422),
            ({"name": "test_name"}, 422),
            ({"price": 10.00}, 422),
            ({"name": "test_name", "description": "test"}, 422),
        ),
    )
    async def test_invalid_input_raises_error(
        self, app: FastAPI, client: AsyncClient, invalid_payload: dict, status_code: int
    ) -> None:
        res = await client.post(app.url_path_for("cleanings:create-cleaning"), json={"new_cleaning": invalid_payload})
        assert res.status_code == status_code


class TestGetCleaning:
    async def test_get_cleaning_by_id(self, app: FastAPI, client: AsyncClient, test_cleaning: CleaningInDB) -> None:
        res = await client.get(app.url_path_for("cleanings:get-cleaning-by-id", id=test_cleaning.id))
        assert res.status_code == HTTP_200_OK
        cleaning = CleaningInDB(**res.json())
        assert cleaning == test_cleaning

    @pytest.mark.parametrize(
        "id, status_code", ((500, 404), (-1, 404), (None, 422),),
    )
    async def test_wrong_id_returns_error(self, app: FastAPI, client: AsyncClient, id: int, status_code: int) -> None:
        res = await client.get(app.url_path_for("cleanings:get-cleaning-by-id", id=id))
        assert res.status_code == status_code

    async def test_get_all_cleanings_returns_valid_response(
        self, app: FastAPI, client: AsyncClient, test_cleaning: CleaningInDB
    ) -> None:
        res = await client.get(app.url_path_for("cleanings:get-all-cleanings"))
        assert res.status_code == HTTP_200_OK
        assert isinstance(res.json(), list)
        assert len(res.json()) > 0
        cleanings = [CleaningInDB(**l) for l in res.json()]
        assert test_cleaning in cleanings


# ...other code


class TestUpdateCleaning:
    @pytest.mark.parametrize(
        "attrs_to_change, values",
        (
            (["name"], ["new fake cleaning name"]),
            (["description"], ["new fake cleaning description"]),
            (["price"], [3.14]),
            (["cleaning_type"], ["full_clean"]),
            (["name", "description"], ["extra new fake cleaning name", "extra new fake cleaning description"]),
            (["price", "cleaning_type"], [42.00, "dust_up"]),
        ),
    )
    async def test_update_cleaning_with_valid_input(
        self,
        app: FastAPI,
        client: AsyncClient,
        test_cleaning: CleaningInDB,
        attrs_to_change: List[str],
        values: List[str],
    ) -> None:
        cleaning_update = {"cleaning_update": {attrs_to_change[i]: values[i] for i in range(len(attrs_to_change))}}

        res = await client.put(
            app.url_path_for("cleanings:update-cleaning-by-id", id=test_cleaning.id), json=cleaning_update
        )
        assert res.status_code == HTTP_200_OK
        updated_cleaning = CleaningInDB(**res.json())
        assert updated_cleaning.id == test_cleaning.id  # make sure it's the same cleaning
        # make sure that any attribute we updated has changed to the correct value
        for i in range(len(attrs_to_change)):
            assert getattr(updated_cleaning, attrs_to_change[i]) != getattr(test_cleaning, attrs_to_change[i])
            assert getattr(updated_cleaning, attrs_to_change[i]) == values[i]
        # make sure that no other attributes' values have changed
        for attr, value in updated_cleaning.dict().items():
            if attr not in attrs_to_change:
                assert getattr(test_cleaning, attr) == value

    @pytest.mark.parametrize(
        "id, payload, status_code",
        (
            (-1, {"name": "test"}, 422),
            (0, {"name": "test2"}, 422),
            (500, {"name": "test3"}, 404),
            (1, None, 422),
            (1, {"cleaning_type": "invalid cleaning type"}, 422),
            (1, {"cleaning_type": None}, 400),
        ),
    )
    async def test_update_cleaning_with_invalid_input_throws_error(
        self, app: FastAPI, client: AsyncClient, id: int, payload: dict, status_code: int,
    ) -> None:
        cleaning_update = {"cleaning_update": payload}

        res = await client.put(app.url_path_for("cleanings:update-cleaning-by-id", id=id), json=cleaning_update)
        assert res.status_code == status_code


# ...other code


class TestDeleteCleaning:
    async def test_can_delete_cleaning_successfully(
        self, app: FastAPI, client: AsyncClient, test_cleaning: CleaningInDB
    ) -> None:
        # delete the cleaning
        res = await client.delete(app.url_path_for("cleanings:delete-cleaning-by-id", id=test_cleaning.id))
        assert res.status_code == HTTP_200_OK
        # ensure that the cleaning no longer exists
        res = await client.get(app.url_path_for("cleanings:get-cleaning-by-id", id=test_cleaning.id))
        assert res.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        "id, status_code", ((500, 404), (0, 422), (-1, 422), (None, 422),),
    )
    async def test_can_delete_cleaning_successfully(
        self, app: FastAPI, client: AsyncClient, test_cleaning: CleaningInDB, id: int, status_code: int
    ) -> None:
        res = await client.delete(app.url_path_for("cleanings:delete-cleaning-by-id", id=id))
        assert res.status_code == status_code

