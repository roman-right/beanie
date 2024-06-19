# Session Handling

When sessions are required to enable transactional rollbacks, atomically the write methods inherited from the `Document` 
class can be used. We can pass a `session` argument to the write methods to enable session handling.

## Sessions In Document Read/Write Methods

Let's define a document and initialize it to be used:

```python
from beanie import Document, init_beanie
import motor.motor_asyncio

class Bike(Document):
    number_of_wheels: int
    color: str
    brand: str


async def main():
    uri = "mongodb://beanie:beanie@localhost:27017"
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    db = client.bikes

    await init_beanie(
        database=db, 
        document_models=[Bike],
    )

    async with await client.start_session() as session:
        async with session.start_transaction():
            bike = Bike(
                number_of_wheels=2,
                color="red",
                brand="Yamaha"
            )
            await bike.insert_one(session=session)
        
            bike_from_db = await Bike.get(bike.id, session=session)
            print(bike_from_db)
```

The above will print out to:

```
>>> Bike(number_of_wheels=2, color="red", brand="BMX")
```

All is good and the session is working as expected. But notice that we have to pass a `session` argument to each of the 
write methods. This can be cumbersome and error-prone. To avoid this, we can initialize the document with a session.

## Documents With Session

In many use cases, when we need to make sure database transactions are rolled back atomically triggered by an exception 
or any other conditions, database sessions are required to make this happen. To avoid passing the `session` argument to 
every read/write methods of the document, we can initialize the document with a session.

Let's take the first example and modify it to initialize the document with a session:

```python
from contextlib import asynccontextmanager
from typing import List

from beanie import Document, init_beanie
import motor.motor_asyncio


class Bike(Document):
    number_of_wheels: int
    color: str
    brand: str


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


async def main():
    uri = "mongodb://beanie:beanie@localhost:27017"
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    db = client.bikes

    await init_beanie(
        database=db, 
        document_models=[Bike],
    )

    async with await with_session(client=client, collections=[Bike]) as session:
        bike = Bike(
            number_of_wheels=2,
            color="red",
            brand="Yamaha"
        )
        await bike.insert_one(session=session)
        raise Exception("Something went wrong, rollback please")
    
    bike_from_db = await Bike.get(bike.id, session=session)
    print(bike_from_db)
```

In this case, stdout will print out:

```
>>> None
```

With the example above, we can be certain that the transaction will be rolled back if an exception is raised.
