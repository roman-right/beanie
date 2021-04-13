import importlib.util
import logging
from pathlib import Path
from typing import Type, Optional

from beanie.odm.documents import Document
from beanie.odm.general import init_beanie
from beanie.migrations.controllers.iterative import BaseMigrationController
from beanie.migrations.database import DBHandler
from beanie.migrations.models import (
    MigrationLog,
    RunningMode,
    RunningDirections,
)

logger = logging.getLogger(__name__)


class MigrationNode:
    def __init__(
        self,
        name: str,
        forward_class: Optional[Type[Document]] = None,
        backward_class: Optional[Type[Document]] = None,
        next_migration: Optional["MigrationNode"] = None,
        prev_migration: Optional["MigrationNode"] = None,
    ):
        """
        TODO doc it
        :param name:
        :param forward_class:
        :param backward_class:
        :param next_migration:
        :param prev_migration:
        """
        self.name = name
        self.forward_class = forward_class
        self.backward_class = backward_class
        self.next_migration = next_migration
        self.prev_migration = prev_migration

    @staticmethod
    async def clean_current_migration():
        await MigrationLog.update_many(
            {"is_current": True}, {"$set": {"is_current": False}}
        )

    async def update_current_migration(self):
        """
        TODO doc it
        :return:
        """
        await self.clean_current_migration()
        await MigrationLog(is_current=True, name=self.name).create()

    async def run(self, mode: RunningMode):
        """
        TODO doc it
        :param mode:
        :return:
        """
        if mode.direction == RunningDirections.FORWARD:
            migration_node = self.next_migration
            if migration_node is None:
                return None
            if mode.distance == 0:
                logger.info("Running migrations forward without limit")
                while True:
                    await migration_node.run_forward()
                    migration_node = migration_node.next_migration
                    if migration_node is None:
                        break
            else:
                logger.info(f"Running {mode.distance} migrations forward")
                for i in range(mode.distance):
                    await migration_node.run_forward()
                    migration_node = migration_node.next_migration
                    if migration_node is None:
                        break
        elif mode.direction == RunningDirections.BACKWARD:
            migration_node = self
            if mode.distance == 0:
                logger.info("Running migrations backward without limit")
                while True:
                    await migration_node.run_backward()
                    migration_node = migration_node.prev_migration
                    if migration_node is None:
                        break
            else:
                logger.info(f"Running {mode.distance} migrations backward")
                for i in range(mode.distance):
                    await migration_node.run_backward()
                    migration_node = migration_node.prev_migration
                    if migration_node is None:
                        break

    async def run_forward(self):
        if self.forward_class is not None:
            await self.run_migration_class(self.forward_class)
        await self.update_current_migration()

    async def run_backward(self):
        if self.backward_class is not None:
            await self.run_migration_class(self.backward_class)
        if self.prev_migration is not None:
            await self.prev_migration.update_current_migration()
        else:
            await self.clean_current_migration()

    async def run_migration_class(self, cls: Type):
        """
        TODO doc it
        :param cls:
        :return:
        """
        migrations = [
            getattr(cls, migration)
            for migration in dir(cls)
            if isinstance(getattr(cls, migration), BaseMigrationController)
        ]

        client = DBHandler().get_cli()
        db = DBHandler().get_db()

        async with await client.start_session() as s:
            async with s.start_transaction():
                models = []
                for migration in migrations:
                    models += migration.models

                await init_beanie(database=db, document_models=models)

                for migration in migrations:
                    logger.info(
                        f"Running migration {migration.function.__name__} "
                        f"from module {self.name}"
                    )
                    await migration.run(session=s)

    @classmethod
    async def build(cls, path: Path):
        """
        TODO doc it
        :param path:
        :return:
        """
        logger.info("Building migration list")
        names = []
        for module in path.glob("*.py"):
            names.append(module.name)
        names.sort()

        db = DBHandler().get_db()
        await init_beanie(database=db, document_models=[MigrationLog])
        current_migration = await MigrationLog.find_one({"is_current": True})

        root_migration_node = MigrationNode("root")
        prev_migration_node = root_migration_node

        for name in names:
            spec = importlib.util.spec_from_file_location(
                (path / name).stem, (path / name).absolute()
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            forward_class = getattr(module, "Forward", None)
            backward_class = getattr(module, "Backward", None)
            migration_node = MigrationNode(
                name=name,
                prev_migration=prev_migration_node,
                forward_class=forward_class,
                backward_class=backward_class,
            )
            prev_migration_node.next_migration = migration_node
            prev_migration_node = migration_node

            if (
                current_migration is not None
                and current_migration.name == name
            ):
                root_migration_node = migration_node

        return root_migration_node
