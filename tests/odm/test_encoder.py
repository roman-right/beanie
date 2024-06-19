import re
from datetime import date, datetime, time
from datetime import timezone as dt_timezone
from typing import Union
from uuid import uuid4

import pytest
from bson import Binary, Regex
from pydantic import AnyUrl

# support for older python versions (will cause to test some things twice)
from pytz import UTC, all_timezones, timezone

from beanie.odm.utils.encoder import Encoder
from beanie.odm.utils.pydantic import IS_PYDANTIC_V2
from tests.odm.models import (
    Child,
    DocumentForEncodingTest,
    DocumentForEncodingTestDate,
    DocumentForEncodingTestTime,
    DocumentWithComplexDictKey,
    DocumentWithDecimalField,
    DocumentWithHttpUrlField,
    DocumentWithKeepNullsFalse,
    DocumentWithStringField,
    ModelWithOptionalField,
    SampleWithMutableObjects,
)

has_zone_info = True
try:
    from zoneinfo import ZoneInfo, available_timezones
except ImportError:
    has_zone_info = False
    ZoneInfo = timezone


async def test_encode_datetime():
    assert isinstance(Encoder().encode(datetime.now()), datetime)

    doc = DocumentForEncodingTest(datetime_field=datetime.now())
    await doc.insert()
    new_doc = await DocumentForEncodingTest.get(doc.id)
    assert isinstance(new_doc.datetime_field, datetime)


async def test_encode_date():
    assert isinstance(Encoder().encode(datetime.now()), datetime)

    doc = DocumentForEncodingTestDate()
    await doc.insert()
    new_doc = await DocumentForEncodingTestDate.get(doc.id)
    assert new_doc.date_field == doc.date_field
    assert isinstance(new_doc.date_field, date)


async def test_encode_regex():
    raw_regex = r"^AA.*CC$"
    case_sensitive_regex = re.compile(raw_regex)
    case_insensitive_regex = re.compile(raw_regex, re.I)

    assert isinstance(Encoder().encode(case_sensitive_regex), Regex)
    assert isinstance(Encoder().encode(case_insensitive_regex), Regex)

    matching_doc = DocumentWithStringField(string_field="AABBCC")
    ignore_case_matching_doc = DocumentWithStringField(string_field="aabbcc")
    non_matching_doc = DocumentWithStringField(string_field="abc")

    for doc in (matching_doc, ignore_case_matching_doc, non_matching_doc):
        await doc.insert()

    assert {matching_doc.id, ignore_case_matching_doc.id} == {
        doc.id
        async for doc in DocumentWithStringField.find(
            DocumentWithStringField.string_field == case_insensitive_regex
        )
    }
    assert {matching_doc.id} == {
        doc.id
        async for doc in DocumentWithStringField.find(
            DocumentWithStringField.string_field == case_sensitive_regex
        )
    }


def test_encode_with_custom_encoder():
    assert isinstance(
        Encoder(custom_encoders={datetime: str}).encode(datetime.now()), str
    )


async def test_bytes():
    encoded_b = Encoder().encode(b"test")
    assert isinstance(encoded_b, Binary)
    assert encoded_b.subtype == 0

    doc = DocumentForEncodingTest(bytes_field=b"test")
    await doc.insert()
    new_doc = await DocumentForEncodingTest.get(doc.id)
    assert isinstance(new_doc.bytes_field, bytes)


async def test_bytes_already_binary():
    b = Binary(b"123", 3)
    encoded_b = Encoder().encode(b)
    assert isinstance(encoded_b, Binary)
    assert encoded_b.subtype == 3


async def test_mutable_objects_on_save():
    instance = SampleWithMutableObjects(
        d={"Bar": Child(child_field="Foo")}, lst=[Child(child_field="Bar")]
    )
    await instance.save()
    assert isinstance(instance.d["Bar"], Child)
    assert isinstance(instance.lst[0], Child)


async def test_decimal():
    test_amts = DocumentWithDecimalField(amt=1, other_amt=2)
    await test_amts.insert()
    obj = await DocumentWithDecimalField.get(test_amts.id)
    assert obj.amt == 1
    assert obj.other_amt == 2

    test_amts.amt = 6
    await test_amts.save_changes()

    obj = await DocumentWithDecimalField.get(test_amts.id)
    assert obj.amt == 6

    test_amts = (await DocumentWithDecimalField.find_all().to_list())[0]
    test_amts.other_amt = 7
    await test_amts.save_changes()

    obj = await DocumentWithDecimalField.get(test_amts.id)
    assert obj.other_amt == 7


def test_keep_nulls_false():
    model = ModelWithOptionalField(i=10)
    doc = DocumentWithKeepNullsFalse(m=model)

    encoder = Encoder(keep_nulls=False, to_db=True)
    encoded_doc = encoder.encode(doc)
    assert encoded_doc == {"m": {"i": 10}}


@pytest.mark.skipif(not IS_PYDANTIC_V2, reason="Test only for Pydantic v2")
def test_should_encode_pydantic_v2_url_correctly():
    url = AnyUrl("https://example.com")
    encoder = Encoder()
    encoded_url = encoder.encode(url)
    assert isinstance(encoded_url, str)
    # pydantic2 add trailing slash for naked url. see https://github.com/pydantic/pydantic/issues/6943
    assert encoded_url == "https://example.com/"


async def test_should_be_able_to_save_retrieve_doc_with_url():
    doc = DocumentWithHttpUrlField(url_field="https://example.com")
    assert isinstance(doc.url_field, AnyUrl)
    await doc.save()

    new_doc = await DocumentWithHttpUrlField.find_one(
        DocumentWithHttpUrlField.id == doc.id
    )

    assert isinstance(new_doc.url_field, AnyUrl)
    assert new_doc.url_field == doc.url_field


async def test_dict_with_complex_key():
    assert isinstance(Encoder().encode({uuid4(): datetime.now()}), dict)

    uuid = uuid4()
    # reset microseconds, because it looses by mongo
    dt = datetime.now().replace(microsecond=0)

    doc = DocumentWithComplexDictKey(dict_field={uuid: dt})
    await doc.insert()
    new_doc = await DocumentWithComplexDictKey.get(doc.id)

    assert isinstance(new_doc.dict_field, dict)
    assert new_doc.dict_field.get(uuid) == dt


def is_same_type_or_subtype(obj1, obj2):
    return isinstance(obj1, type(obj2)) or isinstance(obj2, type(obj1))


def assert_time_equal(to_test: time, reference: time):
    if to_test.tzinfo is not None:  # tz
        if reference.tzinfo.utcoffset(None) is None:
            now = datetime(
                1970, 1, 1, 0, 0, 0, 0
            )  # date dependsent because of daylight saving time

            check_tz_info(to_test, reference, now)
            # compare without info
            assert to_test.replace(tzinfo=None) == reference.replace(
                tzinfo=None
            )
        else:
            check_tz_info(to_test, reference)
            assert to_test.replace(tzinfo=None) == reference.replace(
                tzinfo=None
            )
    else:
        assert to_test == reference


def check_tz_info(
    to_test: time, reference: time, when: Union[datetime, None] = None
):
    # up to 1-minute (not included) difference is allowed by serialization standard used by pydantic
    assert (
        to_test.tzinfo.utcoffset(when).total_seconds() // 60
        == reference.tzinfo.utcoffset(when).total_seconds() // 60
    )


async def inner_test_time(test_time: time):
    doc = DocumentForEncodingTestTime(time_field=test_time)
    await doc.insert()
    new_doc = await DocumentForEncodingTestTime.get(doc.id)
    assert_time_equal(new_doc.time_field, doc.time_field)
    assert isinstance(new_doc.time_field, time)
    assert_time_equal(new_doc.time_field, test_time)


@pytest.mark.parametrize(
    "test_time",
    [
        time(12),
        time(12, fold=1),
        time(12, 3),
        time(12, 3, fold=1),
        time(12, 4, 5),
        time(12, 4, 5, fold=1),
        time(12, 4, 5, 123456),
        time(12, 4, 5, 123456, fold=1),
        time(12, 4, 5, 123456, tzinfo=UTC),
        time(12, 4, 5, 123456, tzinfo=timezone("Europe/Prague")),
        time(12, 4, 5, 123456, tzinfo=UTC, fold=1),
        time(12, 4, 5, 123456, tzinfo=timezone("Europe/Prague")),
        time(12, 4, 5, 123456, tzinfo=timezone("Europe/Prague"), fold=1),
        time(12, 4, 5, 123456, tzinfo=dt_timezone.utc),
        time(12, 4, 5, 123456, tzinfo=dt_timezone.utc, fold=1),
        time(12, 4, 5, 123456, tzinfo=ZoneInfo("Europe/Prague")),
        time(12, 4, 5, 123456, tzinfo=ZoneInfo("Europe/Prague"), fold=1),
    ],
)
async def test_encode_time_with_tz(test_time: time):
    await inner_test_time(test_time)


if has_zone_info:
    tz = list(available_timezones())
    tz.sort()

    @pytest.mark.parametrize("tz_string", tz)
    async def test_encode_time_exhaustive_timezones_zone_info(tz_string: str):
        await inner_test_time(
            time(12, 4, 5, 123456, tzinfo=ZoneInfo(tz_string))
        )


# folowing causes pytz.exceptions.NonExistentTimeError
pytz_unsupported = (
    "America/Bahia_Banderas",
    "America/Hermosillo",
    "America/Mazatlan",
    "Mexico/BajaSur",
)


@pytest.mark.parametrize(
    "tz_string",
    list(filter(lambda x: x not in pytz_unsupported, all_timezones)),
)
async def test_encode_time_exhaustive_timezones_pytz(tz_string: str):
    await inner_test_time(time(12, 4, 5, 123456, tzinfo=timezone(tz_string)))
