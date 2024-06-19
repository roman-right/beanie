from contextlib import asynccontextmanager
from typing import List

import motor.motor_asyncio

from beanie import Document, init_beanie
from tests.odm.models import DocumentTestModelWithCustomCollectionName, SubDocument


@asynccontextmanager
async def with_session(*, client: motor.motor_asyncio.AsyncIOMotorClient, collections: List[Document] | None = None):
    async with await client.start_session() as session:
        async with session.start_transaction():
            try:
                if collections and isinstance(collections, list) and len(collections) > 0:
                    for collection in collections:
                        collection.set_session(session)
                yield session
            except Exception:
                await session.abort_transaction()
            else:
                await session.commit_transaction()
            finally:
                if collections and isinstance(collections, list) and len(collections) > 0:
                    for collection in collections:
                        collection.clear_session()


class DocumentWithSession(Document):
    prop1: int
    prop2: str


class TestDocumentSession:
    async def test_document_session_in_place_rollback(self, cli: motor.motor_asyncio.AsyncIOMotorClient):
        async with with_session(client=cli) as _session:
            subdoc = SubDocument(test_str="test_subdoc", test_int=528)
            doc = DocumentTestModelWithCustomCollectionName(test_int=7, test_list=[subdoc], test_str="test")
            await doc.save(session=_session)

            assert doc.id is not None
            raise Exception("Rollback")

        doc = await DocumentTestModelWithCustomCollectionName.get(doc.id)

        assert doc is None

    async def test_document_session_with_custom_doc_rollback(self, cli: motor.motor_asyncio.AsyncIOMotorClient):
        await init_beanie(cli["beanie_db"], document_models=[DocumentWithSession])

        async with with_session(client=cli, collections=[DocumentWithSession]) as _session:
            doc = DocumentWithSession(prop1=7, prop2="test")
            await doc.save()

            assert doc.id is not None
            raise Exception("Rollback")

        doc = await DocumentWithSession.get(doc.id)

        assert doc is None
