from tests.odm.query_builder.models import Sample


async def test_delete_many(preset_documents):
    count_before = await Sample.count()
    count_find = (
        await Sample.find_many(Sample.integer > 1)
        .find_many(Sample.nested.optional == None)
        .count()
    )  # noqa
    await Sample.find_many(Sample.integer > 1).find_many(
        Sample.nested.optional == None
    ).delete()  # noqa
    count_after = await Sample.count()
    assert count_before - count_find == count_after


async def test_delete_all(preset_documents):
    await Sample.delete_all()
    count_after = await Sample.count()
    assert count_after == 0


async def test_delete_self(preset_documents):
    count_before = await Sample.count()
    result = (
        await Sample.find_many(Sample.integer > 1)
        .find_many(Sample.nested.optional == None)
        .to_list()
    )  # noqa
    a = result[0]
    await a.delete()
    count_after = await Sample.count()
    assert count_before == count_after + 1


async def test_delete_one(preset_documents):
    count_before = await Sample.count()
    await Sample.find_one(Sample.integer > 1).find_one(
        Sample.nested.optional == None
    ).delete()  # noqa
    count_after = await Sample.count()
    assert count_before == count_after + 1
