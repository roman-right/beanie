from contextlib import asynccontextmanager

import motor.motor_asyncio
from fastapi import FastAPI

from beanie import init_beanie
from tests.conftest import Settings
from tests.fastapi.models import DoorAPI, HouseAPI, RoofAPI, WindowAPI
from tests.fastapi.routes import house_router


@asynccontextmanager
async def live_span(_: FastAPI):
    # CREATE MOTOR CLIENT
    client = motor.motor_asyncio.AsyncIOMotorClient(Settings().mongodb_dsn)

    # INIT BEANIE
    await init_beanie(
        client.beanie_db,
        document_models=[HouseAPI, WindowAPI, DoorAPI, RoofAPI],
    )
    yield


app = FastAPI(lifespan=live_span)

# ADD ROUTES
app.include_router(house_router, prefix="/v1", tags=["house"])
