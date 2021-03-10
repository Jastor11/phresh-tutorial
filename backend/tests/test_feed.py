from typing import List
from collections import Counter
import datetime

import pytest

from httpx import AsyncClient
from fastapi import FastAPI, status

from app.models.cleaning import CleaningInDB


pytestmark = pytest.mark.asyncio


class TestFeedRoutes:
    async def test_routes_exist(self, app: FastAPI, client: AsyncClient) -> None:
        res = await client.get(app.url_path_for("feed:get-cleaning-feed-for-user"))
        assert res.status_code != status.HTTP_404_NOT_FOUND


class TestCleaningFeed:
    async def test_cleaning_feed_returns_valid_response(
        self,
        *,
        app: FastAPI,
        authorized_client: AsyncClient,
        test_list_of_new_and_updated_cleanings: List[CleaningInDB],
    ) -> None:
        cleaning_ids = [cleaning.id for cleaning in test_list_of_new_and_updated_cleanings]

        res = await authorized_client.get(app.url_path_for("feed:get-cleaning-feed-for-user"))
        assert res.status_code == status.HTTP_200_OK
        cleaning_feed = res.json()
        assert isinstance(cleaning_feed, list)
        assert len(cleaning_feed) == 20
        assert set(feed_item["id"] for feed_item in cleaning_feed).issubset(set(cleaning_ids))

    async def test_cleaning_feed_response_is_ordered_correctly(
        self,
        *,
        app: FastAPI,
        authorized_client: AsyncClient,
        # test_list_of_new_and_updated_cleanings: List[CleaningInDB],
    ) -> None:
        res = await authorized_client.get(app.url_path_for("feed:get-cleaning-feed-for-user"))
        assert res.status_code == status.HTTP_200_OK
        cleaning_feed = res.json()

        # the first 13 should be updated and the rest should not be updated
        for feed_item in cleaning_feed[:13]:
            assert feed_item["event_type"] == "is_update"
        for feed_item in cleaning_feed[13:]:
            assert feed_item["event_type"] == "is_create"

    async def test_cleaning_feed_can_paginate_correctly(
        self,
        *,
        app: FastAPI,
        authorized_client: AsyncClient,
        test_list_of_new_and_updated_cleanings: List[CleaningInDB],
    ) -> None:
        starting_date = datetime.datetime.now() + datetime.timedelta(minutes=10)
        combos = []
        for chunk_size in [25, 15, 10]:
            res = await authorized_client.get(
                app.url_path_for("feed:get-cleaning-feed-for-user"),
                params={"starting_date": starting_date, "page_chunk_size": chunk_size},
            )
            assert res.status_code == status.HTTP_200_OK
            page_json = res.json()
            assert len(page_json) == chunk_size
            id_and_event_combo = set(f"{item['id']}-{item['event_type']}" for item in page_json)
            combos.append(id_and_event_combo)
            starting_date = page_json[-1]["event_timestamp"]
        # Ensure that none of the items in any response exist in any other response
        length_of_all_id_combos = sum(len(combo) for combo in combos)
        assert len(set().union(*combos)) == length_of_all_id_combos

    async def test_cleaning_feed_has_created_and_updated_items_for_modified_cleaning_jobs(
        self,
        *,
        app: FastAPI,
        authorized_client: AsyncClient,
        test_list_of_new_and_updated_cleanings: List[CleaningInDB],
    ) -> None:
        res_page_1 = await authorized_client.get(
            app.url_path_for("feed:get-cleaning-feed-for-user"), params={"page_chunk_size": 30},
        )
        assert res_page_1.status_code == status.HTTP_200_OK
        ids_page_1 = [feed_item["id"] for feed_item in res_page_1.json()]

        new_starting_date = res_page_1.json()[-1]["updated_at"]

        res_page_2 = await authorized_client.get(
            app.url_path_for("feed:get-cleaning-feed-for-user"),
            params={"starting_date": new_starting_date, "page_chunk_size": 33},
        )
        assert res_page_2.status_code == status.HTTP_200_OK
        ids_page_2 = [feed_item["id"] for feed_item in res_page_2.json()]

        # should have duplicate IDs for the 13 updated events - an `is_create` event and an `is_update` event
        id_counts = Counter(ids_page_1 + ids_page_2)
        assert len([id for id, cnt in id_counts.items() if cnt > 1]) == 13
