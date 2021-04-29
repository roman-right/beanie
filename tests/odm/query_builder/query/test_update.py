from beanie.odm.operators.update.general import Set, Max
from tests.odm.query_builder.models import Sample


async def test_update_query():
    q = (
        Sample.find_many(Sample.integer == 1)
        .update(Set({Sample.integer: 10}))
        .update_query
    )
    assert q == {"$set": {"integer": 10}}

    q = (
        Sample.find_many(Sample.integer == 1)
        .update(Max({Sample.integer: 10}), Set({Sample.optional: None}))
        .update_query
    )
    assert q == {"$max": {"integer": 10}, "$set": {"optional": None}}

    q = (
        Sample.find_many(Sample.integer == 1)
        .update(Set({Sample.integer: 10}), Set({Sample.optional: None}))
        .update_query
    )
    assert q == {"$set": {"optional": None}}

    q = (
        Sample.find_many(Sample.integer == 1)
        .update(Max({Sample.integer: 10}))
        .update(Set({Sample.optional: None}))
        .update_query
    )
    assert q == {"$max": {"integer": 10}, "$set": {"optional": None}}

    q = (
        Sample.find_many(Sample.integer == 1)
        .update(Set({Sample.integer: 10}))
        .update(Set({Sample.optional: None}))
        .update_query
    )
    assert q == {"$set": {"optional": None}}


async def test_update_many(preset_documents):
    await Sample.find_many(Sample.increment > 4).find_many(
        Sample.nested.optional == None
    ).update(
        Set({Sample.increment: 100})
    )  # noqa
    result = await Sample.find_many(Sample.increment == 100).to_list()
    assert len(result) == 3
    for sample in result:
        assert sample.increment == 100


async def test_update_all(preset_documents):
    await Sample.update_all(Set({Sample.integer: 100}))
    result = await Sample.find_all().to_list()
    for sample in result:
        assert sample.integer == 100

    await Sample.find_all().update(Set({Sample.integer: 101}))
    result = await Sample.find_all().to_list()
    for sample in result:
        assert sample.integer == 101


async def test_update_one(preset_documents):
    await Sample.find_one(Sample.integer == 1).update(
        Set({Sample.integer: 100})
    )
    result = await Sample.find_many(Sample.integer == 100).to_list()
    assert len(result) == 1
    assert result[0].integer == 100


async def test_update_self(preset_documents):
    sample = await Sample.find_one(Sample.integer == 1)
    await sample.update(Set({Sample.integer: 100}))
    assert sample.integer == 100

    result = await Sample.find_many(Sample.integer == 100).to_list()
    assert len(result) == 1
    assert result[0].integer == 100


async def test_update_many_with_session(preset_documents, session):
    q = (
        Sample.find_many(Sample.increment > 4)
        .find_many(Sample.nested.optional == None)
        .update(Set({Sample.increment: 100}))
        .set_session(session=session)
    )
    assert q.session == session

    q = (
        Sample.find_many(Sample.increment > 4)
        .find_many(Sample.nested.optional == None)
        .update(Set({Sample.increment: 100}), session=session)
    )
    assert q.session == session

    q = (
        Sample.find_many(Sample.increment > 4)
        .find_many(Sample.nested.optional == None, session=session)
        .update(Set({Sample.increment: 100}))
    )
    assert q.session == session

    await q  # noqa
    result = await Sample.find_many(Sample.increment == 100).to_list()
    assert len(result) == 3
    for sample in result:
        assert sample.increment == 100
