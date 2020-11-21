import warnings
import uuid
import os
import random
from typing import List, Callable

import pytest
import docker as pydocker
from asgi_lifespan import LifespanManager

from fastapi import FastAPI
from httpx import AsyncClient
from databases import Database

import alembic
from alembic.config import Config

from app.models.cleaning import CleaningCreate, CleaningInDB
from app.db.repositories.cleanings import CleaningsRepository

from app.models.user import UserCreate, UserInDB
from app.db.repositories.users import UsersRepository

from app.models.offer import OfferCreate, OfferUpdate
from app.db.repositories.offers import OffersRepository

from app.models.evaluation import EvaluationCreate
from app.db.repositories.evaluations import EvaluationsRepository

from app.core.config import SECRET_KEY, JWT_TOKEN_PREFIX
from app.services import auth_service


@pytest.fixture(scope="session")
def docker() -> pydocker.APIClient:
    # base url is the unix socket we use to communicate with docker
    return pydocker.APIClient(base_url="unix://var/run/docker.sock", version="auto")


@pytest.fixture(scope="session", autouse=True)
def postgres_container(docker: pydocker.APIClient) -> None:
    """
    Use docker to spin up a postgres container for the duration of the testing session.

    Kill it as soon as all tests are run.

    DB actions persist across the entirety of the testing session.
    """
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    # pull image from docker
    image = "postgres:12.1-alpine"
    docker.pull(image)

    # create the new container using
    # the same image used by our database
    container = docker.create_container(image=image, name=f"test-postgres-{uuid.uuid4()}", detach=True,)

    docker.start(container=container["Id"])

    config = Config("alembic.ini")

    try:
        os.environ["DB_SUFFIX"] = "_test"
        alembic.command.upgrade(config, "head")
        yield container
        alembic.command.downgrade(config, "base")
    finally:
        # remove container
        docker.kill(container["Id"])
        docker.remove_container(container["Id"])


# Create a new application for testing
@pytest.fixture
def app() -> FastAPI:
    from app.api.server import get_application

    return get_application()


# Grab a reference to our database when needed
@pytest.fixture
def db(app: FastAPI) -> Database:
    return app.state._db


async def create_cleaning_with_evaluated_offer_helper(
    db: Database,
    owner: UserInDB,
    cleaner: UserInDB,
    cleaning_create: CleaningCreate,
    evaluation_create: EvaluationCreate,
) -> CleaningInDB:
    cleaning_repo = CleaningsRepository(db)
    offers_repo = OffersRepository(db)
    evals_repo = EvaluationsRepository(db)

    created_cleaning = await cleaning_repo.create_cleaning(new_cleaning=cleaning_create, requesting_user=owner)
    offer = await offers_repo.create_offer_for_cleaning(
        new_offer=OfferCreate(cleaning_id=created_cleaning.id, user_id=cleaner.id)
    )
    await offers_repo.accept_offer(offer=offer, offer_update=OfferUpdate(status="accepted"))
    await evals_repo.create_evaluation_for_cleaner(
        evaluation_create=evaluation_create, cleaning=created_cleaning, cleaner=cleaner,
    )
    return created_cleaning


@pytest.fixture
async def test_list_of_cleanings_with_evaluated_offer(
    db: Database, test_user2: UserInDB, test_user3: UserInDB,
) -> List[CleaningInDB]:
    return [
        await create_cleaning_with_evaluated_offer_helper(
            db=db,
            owner=test_user2,
            cleaner=test_user3,
            cleaning_create=CleaningCreate(
                name=f"test cleaning - {i}",
                description=f"test description - {i}",
                price=float(f"{i}9.99"),
                cleaning_type="full_clean",
            ),
            evaluation_create=EvaluationCreate(
                professionalism=random.randint(0, 5),
                completeness=random.randint(0, 5),
                efficiency=random.randint(0, 5),
                overall_rating=random.randint(0, 5),
                headline=f"test headline - {i}",
                comment=f"test comment - {i}",
            ),
        )
        for i in range(5)
    ]


@pytest.fixture
async def test_cleaning(db: Database, test_user: UserInDB) -> CleaningInDB:
    cleaning_repo = CleaningsRepository(db)
    new_cleaning = CleaningCreate(
        name="fake cleaning name", description="fake cleaning description", price=9.99, cleaning_type="spot_clean"
    )

    return await cleaning_repo.create_cleaning(new_cleaning=new_cleaning, requesting_user=test_user)


@pytest.fixture
async def test_cleaning_with_offers(db: Database, test_user2: UserInDB, test_user_list: List[UserInDB]) -> CleaningInDB:
    cleaning_repo = CleaningsRepository(db)
    offers_repo = OffersRepository(db)

    new_cleaning = CleaningCreate(
        name="cleaning with offers", description="desc for cleaning", price=9.99, cleaning_type="full_clean",
    )

    created_cleaning = await cleaning_repo.create_cleaning(new_cleaning=new_cleaning, requesting_user=test_user2)

    for user in test_user_list:
        await offers_repo.create_offer_for_cleaning(
            new_offer=OfferCreate(cleaning_id=created_cleaning.id, user_id=user.id)
        )

    return created_cleaning


@pytest.fixture
async def test_cleaning_with_accepted_offer(
    db: Database, test_user2: UserInDB, test_user3: UserInDB, test_user_list: List[UserInDB]
) -> CleaningInDB:
    cleaning_repo = CleaningsRepository(db)
    offers_repo = OffersRepository(db)

    new_cleaning = CleaningCreate(
        name="cleaning with accepted offer",
        description="desc for cleaning with accepted offer",
        price=99.99,
        cleaning_type="full_clean",
    )

    created_cleaning = await cleaning_repo.create_cleaning(new_cleaning=new_cleaning, requesting_user=test_user2)

    offers = []
    for user in test_user_list:
        offers.append(
            await offers_repo.create_offer_for_cleaning(
                new_offer=OfferCreate(cleaning_id=created_cleaning.id, user_id=user.id)
            )
        )

    await offers_repo.accept_offer(
        offer=[o for o in offers if o.user_id == test_user3.id][0], offer_update=OfferUpdate(status="accepted")
    )

    return created_cleaning


async def user_fixture_helper(*, db: Database, new_user: UserCreate) -> UserInDB:
    user_repo = UsersRepository(db)

    existing_user = await user_repo.get_user_by_email(email=new_user.email)
    if existing_user:
        return existing_user

    return await user_repo.register_new_user(new_user=new_user)


@pytest.fixture
async def test_user(db: Database) -> UserInDB:
    new_user = UserCreate(email="lebron@james.io", username="lebronjames", password="heatcavslakers")
    return await user_fixture_helper(db=db, new_user=new_user)


@pytest.fixture
async def test_user2(db: Database) -> UserInDB:
    new_user = UserCreate(email="serena@williams.io", username="serenawilliams", password="tennistwins")
    return await user_fixture_helper(db=db, new_user=new_user)


@pytest.fixture
async def test_user3(db: Database) -> UserInDB:
    new_user = UserCreate(email="brad@pitt.io", username="bradpitt", password="adastra")
    return await user_fixture_helper(db=db, new_user=new_user)


@pytest.fixture
async def test_user4(db: Database) -> UserInDB:
    new_user = UserCreate(email="jennifer@lopez.io", username="jlo", password="jennyfromtheblock")
    return await user_fixture_helper(db=db, new_user=new_user)


@pytest.fixture
async def test_user5(db: Database) -> UserInDB:
    new_user = UserCreate(email="bruce@lee.io", username="brucelee", password="martialarts")
    return await user_fixture_helper(db=db, new_user=new_user)


@pytest.fixture
async def test_user6(db: Database) -> UserInDB:
    new_user = UserCreate(email="kal@penn.io", username="kalpenn", password="haroldandkumar")
    return await user_fixture_helper(db=db, new_user=new_user)


@pytest.fixture
async def test_user_list(
    test_user3: UserInDB, test_user4: UserInDB, test_user5: UserInDB, test_user6: UserInDB,
) -> List[UserInDB]:
    return [test_user3, test_user4, test_user5, test_user6]


# Make requests in our tests
@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with LifespanManager(app):
        async with AsyncClient(
            app=app, base_url="http://testserver", headers={"Content-Type": "application/json"}
        ) as client:
            yield client


@pytest.fixture
def authorized_client(client: AsyncClient, test_user: UserInDB) -> AsyncClient:
    access_token = auth_service.create_access_token_for_user(user=test_user, secret_key=str(SECRET_KEY))

    client.headers = {
        **client.headers,
        "Authorization": f"{JWT_TOKEN_PREFIX} {access_token}",
    }

    return client


@pytest.fixture
def create_authorized_client(client: AsyncClient) -> Callable:
    def _create_authorized_client(*, user: UserInDB) -> AsyncClient:
        access_token = auth_service.create_access_token_for_user(user=user, secret_key=str(SECRET_KEY))

        client.headers = {
            **client.headers,
            "Authorization": f"{JWT_TOKEN_PREFIX} {access_token}",
        }

        return client

    return _create_authorized_client
