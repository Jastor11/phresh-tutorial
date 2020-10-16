import warnings
import uuid
import os

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


@pytest.fixture
async def test_cleaning(db: Database) -> CleaningInDB:
    cleaning_repo = CleaningsRepository(db)
    new_cleaning = CleaningCreate(
        name="fake cleaning name", description="fake cleaning description", price=9.99, cleaning_type="spot_clean",
    )

    return await cleaning_repo.create_cleaning(new_cleaning=new_cleaning)


@pytest.fixture
async def test_user(db: Database) -> UserInDB:
    new_user = UserCreate(email="lebron@james.io", username="lebronjames", password="heatcavslakers")

    user_repo = UsersRepository(db)

    existing_user = await user_repo.get_user_by_email(email=new_user.email)
    if existing_user:
        return existing_user

    return await user_repo.register_new_user(new_user=new_user)


# Make requests in our tests
@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with LifespanManager(app):
        async with AsyncClient(
            app=app, base_url="http://testserver", headers={"Content-Type": "application/json"}
        ) as client:
            yield client
