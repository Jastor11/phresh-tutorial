from typing import List, Callable
from statistics import mean
import pytest

from httpx import AsyncClient
from fastapi import FastAPI, status


from app.models.cleaning import CleaningInDB
from app.models.user import UserInDB
from app.models.offer import OfferInDB
from app.models.evaluation import EvaluationCreate, EvaluationInDB, EvaluationPublic, EvaluationAggregate


pytestmark = pytest.mark.asyncio


class TestEvaluationRoutes:
    async def test_routes_exist(self, app: FastAPI, client: AsyncClient) -> None:
        res = await client.post(
            app.url_path_for("evaluations:create-evaluation-for-cleaner", cleaning_id=1, username="bradpitt")
        )
        assert res.status_code != status.HTTP_404_NOT_FOUND

        res = await client.get(
            app.url_path_for("evaluations:get-evaluation-for-cleaner", cleaning_id=1, username="bradpitt")
        )
        assert res.status_code != status.HTTP_404_NOT_FOUND

        res = await client.get(app.url_path_for("evaluations:list-evaluations-for-cleaner", username="bradpitt"))
        assert res.status_code != status.HTTP_404_NOT_FOUND

        res = await client.get(app.url_path_for("evaluations:get-stats-for-cleaner", username="bradpitt"))
        assert res.status_code != status.HTTP_404_NOT_FOUND


# ...other code


class TestCreateEvaluations:
    async def test_owner_can_leave_evaluation_for_cleaner_and_mark_offer_completed(
        self,
        app: FastAPI,
        create_authorized_client: Callable,
        test_user2: UserInDB,
        test_user3: UserInDB,
        test_cleaning_with_accepted_offer: CleaningInDB,
    ) -> None:
        evaluation_create = EvaluationCreate(
            no_show=False,
            headline="Excellent job",
            comment=f"""
Really appreciated the hard work and effort they put into this job!
Though the cleaner took their time, I would definitely hire them again for the quality of their work.
            """,
            professionalism=5,
            completeness=5,
            efficiency=4,
            overall_rating=5,
        )

        authorized_client = create_authorized_client(user=test_user2)
        res = await authorized_client.post(
            app.url_path_for(
                "evaluations:create-evaluation-for-cleaner",
                cleaning_id=test_cleaning_with_accepted_offer.id,
                username=test_user3.username,
            ),
            json={"evaluation_create": evaluation_create.dict()},
        )
        assert res.status_code == status.HTTP_201_CREATED
        evaluation = EvaluationInDB(**res.json())
        assert evaluation.no_show == evaluation_create.no_show
        assert evaluation.headline == evaluation_create.headline
        assert evaluation.overall_rating == evaluation_create.overall_rating

        # check that the offer has now been marked as "completed"
        res = await authorized_client.get(
            app.url_path_for(
                "offers:get-offer-from-user",
                cleaning_id=test_cleaning_with_accepted_offer.id,
                username=test_user3.username,
            )
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["status"] == "completed"

    async def test_non_owner_cant_leave_review(
        self,
        app: FastAPI,
        create_authorized_client: Callable,
        test_user4: UserInDB,
        test_user3: UserInDB,
        test_cleaning_with_accepted_offer: CleaningInDB,
    ) -> None:
        authorized_client = create_authorized_client(user=test_user4)
        res = await authorized_client.post(
            app.url_path_for(
                "evaluations:create-evaluation-for-cleaner",
                cleaning_id=test_cleaning_with_accepted_offer.id,
                username=test_user3.username,
            ),
            json={"evaluation_create": {"overall_rating": 2}},
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN

    async def test_owner_cant_leave_review_for_wrong_user(
        self,
        app: FastAPI,
        create_authorized_client: Callable,
        test_user2: UserInDB,
        test_user4: UserInDB,
        test_cleaning_with_accepted_offer: CleaningInDB,
    ) -> None:
        authorized_client = create_authorized_client(user=test_user2)
        res = await authorized_client.post(
            app.url_path_for(
                "evaluations:create-evaluation-for-cleaner",
                cleaning_id=test_cleaning_with_accepted_offer.id,
                username=test_user4.username,
            ),
            json={"evaluation_create": {"overall_rating": 1}},
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    async def test_owner_cant_leave_multiple_reviews(
        self,
        app: FastAPI,
        create_authorized_client: Callable,
        test_user2: UserInDB,
        test_user3: UserInDB,
        test_cleaning_with_accepted_offer: CleaningInDB,
    ) -> None:
        authorized_client = create_authorized_client(user=test_user2)
        res = await authorized_client.post(
            app.url_path_for(
                "evaluations:create-evaluation-for-cleaner",
                cleaning_id=test_cleaning_with_accepted_offer.id,
                username=test_user3.username,
            ),
            json={"evaluation_create": {"overall_rating": 3}},
        )
        assert res.status_code == status.HTTP_201_CREATED

        res = await authorized_client.post(
            app.url_path_for(
                "evaluations:create-evaluation-for-cleaner",
                cleaning_id=test_cleaning_with_accepted_offer.id,
                username=test_user3.username,
            ),
            json={"evaluation_create": {"overall_rating": 1}},
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST


class TestGetEvaluations:
    """
    Test that authenticated user who is not owner or cleaner can fetch a single evaluation
    Test that authenticated user can fetch all of a cleaner's evaluations
    Test that a cleaner's evaluations comes with an aggregate
    """

    async def test_authenticated_user_can_get_evaluation_for_cleaning(
        self,
        app: FastAPI,
        create_authorized_client: Callable,
        test_user3: UserInDB,
        test_user4: UserInDB,
        test_list_of_cleanings_with_evaluated_offer: List[CleaningInDB],
    ) -> None:
        authorized_client = create_authorized_client(user=test_user4)
        res = await authorized_client.get(
            app.url_path_for(
                "evaluations:get-evaluation-for-cleaner",
                cleaning_id=test_list_of_cleanings_with_evaluated_offer[0].id,
                username=test_user3.username,
            )
        )
        assert res.status_code == status.HTTP_200_OK
        evaluation = EvaluationPublic(**res.json())
        assert evaluation.cleaning_id == test_list_of_cleanings_with_evaluated_offer[0].id
        assert evaluation.cleaner_id == test_user3.id
        assert "test headline" in evaluation.headline
        assert "test comment" in evaluation.comment
        assert evaluation.professionalism >= 0 and evaluation.professionalism <= 5
        assert evaluation.completeness >= 0 and evaluation.completeness <= 5
        assert evaluation.efficiency >= 0 and evaluation.efficiency <= 5
        assert evaluation.overall_rating >= 0 and evaluation.overall_rating <= 5

    async def test_authenticated_user_can_get_list_of_evaluations_for_cleaner(
        self,
        app: FastAPI,
        create_authorized_client: Callable,
        test_user3: UserInDB,
        test_user4: UserInDB,
        # test_list_of_cleanings_with_evaluated_offer: List[CleaningInDB],
    ) -> None:
        authorized_client = create_authorized_client(user=test_user4)
        res = await authorized_client.get(
            app.url_path_for("evaluations:list-evaluations-for-cleaner", username=test_user3.username)
        )
        assert res.status_code == status.HTTP_200_OK
        evaluations = [EvaluationPublic(**e) for e in res.json()]
        assert len(evaluations) > 1
        for evaluation in evaluations:
            assert evaluation.cleaner_id == test_user3.id
            assert evaluation.overall_rating >= 0

    async def test_authenticated_user_can_get_aggregate_stats_for_cleaner(
        self,
        app: FastAPI,
        create_authorized_client: Callable,
        test_user3: UserInDB,
        test_user4: UserInDB,
        test_list_of_cleanings_with_evaluated_offer: List[CleaningInDB],
    ) -> None:
        authorized_client = create_authorized_client(user=test_user4)
        res = await authorized_client.get(
            app.url_path_for("evaluations:list-evaluations-for-cleaner", username=test_user3.username)
        )
        assert res.status_code == status.HTTP_200_OK
        evaluations = [EvaluationPublic(**e) for e in res.json()]

        res = await authorized_client.get(
            app.url_path_for("evaluations:get-stats-for-cleaner", username=test_user3.username)
        )
        assert res.status_code == status.HTTP_200_OK
        stats = EvaluationAggregate(**res.json())

        assert len(evaluations) == stats.total_evaluations
        assert max([e.overall_rating for e in evaluations]) == stats.max_overall_rating
        assert min([e.overall_rating for e in evaluations]) == stats.min_overall_rating
        assert mean([e.overall_rating for e in evaluations]) == stats.avg_overall_rating
        assert (
            mean([e.professionalism for e in evaluations if e.professionalism is not None]) == stats.avg_professionalism
        )
        assert mean([e.completeness for e in evaluations if e.completeness is not None]) == stats.avg_completeness
        assert mean([e.efficiency for e in evaluations if e.efficiency is not None]) == stats.avg_efficiency
        assert len([e for e in evaluations if e.overall_rating == 1]) == stats.one_stars
        assert len([e for e in evaluations if e.overall_rating == 2]) == stats.two_stars
        assert len([e for e in evaluations if e.overall_rating == 3]) == stats.three_stars
        assert len([e for e in evaluations if e.overall_rating == 4]) == stats.four_stars
        assert len([e for e in evaluations if e.overall_rating == 5]) == stats.five_stars

    async def test_unauthenticated_user_forbidden_from_get_requests(
        self,
        app: FastAPI,
        client: AsyncClient,
        test_user3: UserInDB,
        test_list_of_cleanings_with_evaluated_offer: List[CleaningInDB],
    ) -> None:
        res = await client.get(
            app.url_path_for(
                "evaluations:get-evaluation-for-cleaner",
                cleaning_id=test_list_of_cleanings_with_evaluated_offer[0].id,
                username=test_user3.username,
            )
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

        res = await client.get(
            app.url_path_for("evaluations:list-evaluations-for-cleaner", username=test_user3.username)
        )
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

