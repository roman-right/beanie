import datetime
import sys
from enum import Enum
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv4Network,
    IPv6Address,
    IPv6Interface,
    IPv6Network,
)
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)
from uuid import UUID, uuid4

import pymongo
from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    PrivateAttr,
    SecretBytes,
    SecretStr,
)
from pydantic.fields import FieldInfo
from pydantic_core import core_schema
from pymongo import IndexModel
from typing_extensions import Annotated

from beanie import (
    DecimalAnnotation,
    Document,
    DocumentWithSoftDelete,
    Indexed,
    Insert,
    Replace,
    Save,
    Update,
    ValidateOnSave,
)
from beanie.odm.actions import Delete, after_event, before_event
from beanie.odm.custom_types.bson.binary import BsonBinary
from beanie.odm.fields import BackLink, Link, PydanticObjectId
from beanie.odm.settings.timeseries import TimeSeriesConfig
from beanie.odm.union_doc import UnionDoc
from beanie.odm.utils.pydantic import IS_PYDANTIC_V2

if IS_PYDANTIC_V2:
    from pydantic import RootModel, validate_call

if sys.version_info >= (3, 10):

    def type_union(A, B):
        return A | B

else:

    def type_union(A, B):
        return Union[A, B]


class Color:
    def __init__(self, value):
        self.value = value

    def as_rgb(self):
        return self.value

    def as_hex(self):
        return self.value

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if isinstance(value, Color):
            return value
        if isinstance(value, dict):
            return Color(value["value"])
        return Color(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Callable[[Any], core_schema.CoreSchema],  # type: ignore
    ) -> core_schema.CoreSchema:  # type: ignore
        def validate(value, _: FieldInfo) -> Color:
            if isinstance(value, Color):
                return value
            if isinstance(value, dict):
                return Color(value["value"])
            return Color(value)

        vf = (
            core_schema.with_info_plain_validator_function
            if hasattr(core_schema, "with_info_plain_validator_function")
            else core_schema.general_plain_validator_function
        )
        python_schema = vf(validate)

        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=python_schema,
        )


class Extra(str, Enum):
    allow = "allow"


class Option2(BaseModel):
    f: float


class Option1(BaseModel):
    s: str


class Nested(BaseModel):
    integer: int
    option_1: Option1
    union: Union[Option1, Option2]
    optional: Optional[Option2] = None


class GeoObject(BaseModel):
    type: str = "Point"
    coordinates: Tuple[float, float]


class Sample(Document):
    timestamp: datetime.datetime
    increment: Indexed(int)
    integer: Indexed(int)
    float_num: float
    string: str
    nested: Nested
    optional: Optional[Option2] = None
    union: Union[Option1, Option2]
    geo: GeoObject
    const: str = "TEST"


class DocumentTestModelWithSoftDelete(DocumentWithSoftDelete):
    test_int: int
    test_str: str


class SubDocument(BaseModel):
    test_str: str
    test_int: int = 42


class DocumentTestModel(Document):
    test_int: int
    test_doc: SubDocument
    test_str: str
    test_list: List[SubDocument] = Field(exclude=True)

    class Settings:
        use_cache = True
        cache_expiration_time = datetime.timedelta(seconds=10)
        cache_capacity = 5
        use_state_management = True


class DocumentTestModelWithLink(Document):
    test_link: Link[DocumentTestModel]

    class Settings:
        use_cache = True
        cache_expiration_time = datetime.timedelta(seconds=10)
        cache_capacity = 5
        use_state_management = True


class DocumentTestModelWithCustomCollectionName(Document):
    test_int: int
    test_list: List[SubDocument]
    test_str: str

    class Settings:
        name = "custom"
        class_id = "different_class_id"


class DocumentTestModelWithSimpleIndex(Document):
    test_int: Indexed(int)
    test_list: List[SubDocument]
    test_str: Indexed(str, index_type=pymongo.TEXT)


class DocumentTestModelWithIndexFlags(Document):
    test_int: Indexed(int, sparse=True)
    test_str: Indexed(str, index_type=pymongo.DESCENDING, unique=True)


class DocumentTestModelWithIndexFlagsAliases(Document):
    test_int: Indexed(int, sparse=True) = Field(alias="testInt")
    test_str: Indexed(str, index_type=pymongo.DESCENDING, unique=True) = Field(
        alias="testStr"
    )


class DocumentTestModelIndexFlagsAnnotated(Document):
    str_index: Indexed(str, index_type=pymongo.TEXT)
    str_index_annotated: Indexed(str, index_type=pymongo.ASCENDING)
    uuid_index_annotated: Annotated[UUID4, Indexed(unique=True)]

    if not IS_PYDANTIC_V2:
        # The UUID4 type raises a ValueError with the current
        # implementation of Indexed when using Pydantic v2.
        uuid_index: Indexed(UUID4, unique=True)


class DocumentTestModelWithComplexIndex(Document):
    test_int: int
    test_list: List[SubDocument]
    test_str: str

    class Settings:
        name = "docs_with_index"
        indexes = [
            "test_int",
            [
                ("test_int", pymongo.ASCENDING),
                ("test_str", pymongo.DESCENDING),
            ],
            IndexModel(
                [("test_str", pymongo.DESCENDING)],
                name="test_string_index_DESCENDING",
            ),
        ]


class DocumentTestModelWithDroppedIndex(Document):
    test_int: int
    test_list: List[SubDocument]
    test_str: str

    class Settings:
        name = "docs_with_index"
        indexes = [
            "test_int",
        ]


class DocumentTestModelStringImport(Document):
    test_int: int


class DocumentTestModelFailInspection(Document):
    test_int_2: int

    class Settings:
        name = "DocumentTestModel"


class DocumentWithDeprecatedHiddenField(Document):
    if IS_PYDANTIC_V2:
        test_hidden: List[str] = Field(json_schema_extra={"hidden": True})
    else:
        test_hidden: List[str] = Field(hidden=True)


class DocumentWithCustomIdUUID(Document):
    id: UUID = Field(default_factory=uuid4)
    name: str


class DocumentWithCustomIdInt(Document):
    id: int
    name: str


class DocumentWithCustomFiledsTypes(Document):
    color: Color
    decimal: DecimalAnnotation
    secret_bytes: SecretBytes
    secret_string: SecretStr
    ipv4address: IPv4Address
    ipv4interface: IPv4Interface
    ipv4network: IPv4Network
    ipv6address: IPv6Address
    ipv6interface: IPv6Interface
    ipv6network: IPv6Network
    timedelta: datetime.timedelta
    set_type: Set[str]
    tuple_type: Tuple[int, str]
    path: Path

    class Settings:
        bson_encoders = {Color: vars}

    if IS_PYDANTIC_V2:
        model_config = ConfigDict(
            arbitrary_types_allowed=True,
        )
    else:

        class Config:
            arbitrary_types_allowed = True


class DocumentWithBsonEncodersFiledsTypes(Document):
    color: Color
    timestamp: datetime.datetime

    class Settings:
        bson_encoders = {
            Color: lambda c: c.as_rgb(),
            datetime.datetime: lambda o: o.isoformat(timespec="microseconds"),
        }

    if IS_PYDANTIC_V2:
        model_config = ConfigDict(
            arbitrary_types_allowed=True,
        )
    else:

        class Config:
            arbitrary_types_allowed = True


class DocumentWithActions(Document):
    name: str
    num_1: int = 0
    num_2: int = 10
    num_3: int = 100
    _private_num: int = PrivateAttr(default=100)

    class Inner:
        inner_num_1 = 0
        inner_num_2 = 0

    @before_event(Insert)
    def capitalize_name(self):
        self.name = self.name.capitalize()

    @before_event([Insert, Replace, Save])
    async def add_one(self):
        self.num_1 += 1

    @after_event(Insert)
    def num_2_change(self):
        self.num_2 -= 1

    @after_event(Replace)
    def num_3_change(self):
        self.num_3 -= 1

    @before_event(Delete)
    def inner_num_to_one(self):
        self.Inner.inner_num_1 = 1

    @after_event(Delete)
    def inner_num_to_two(self):
        self.Inner.inner_num_2 = 2

    @before_event(Update)
    def inner_num_to_one_2(self):
        self._private_num += 1

    @after_event(Update)
    def inner_num_to_two_2(self):
        self.num_2 -= 1


class DocumentWithActions2(Document):
    name: str
    num_1: int = 0
    num_2: int = 10
    num_3: int = 100
    _private_num: int = PrivateAttr(default=100)

    class Inner:
        inner_num_1 = 0
        inner_num_2 = 0

    @before_event(Insert)
    def capitalize_name(self):
        self.name = self.name.capitalize()

    @before_event(Insert, Replace, Save)
    async def add_one(self):
        self.num_1 += 1

    @after_event(Insert)
    def num_2_change(self):
        self.num_2 -= 1

    @after_event(Replace)
    def num_3_change(self):
        self.num_3 -= 1

    @before_event(Delete)
    def inner_num_to_one(self):
        self.Inner.inner_num_1 = 1

    @after_event(Delete)
    def inner_num_to_two(self):
        self.Inner.inner_num_2 = 2

    @before_event(Update)
    def inner_num_to_one_2(self):
        self._private_num += 1

    @after_event(Update)
    def inner_num_to_two_2(self):
        self.num_2 -= 1


class InheritedDocumentWithActions(DocumentWithActions):
    ...


class InternalDoc(BaseModel):
    _private_field: str = PrivateAttr(default="TEST_PRIVATE")
    num: int = 100
    string: str = "test"
    lst: List[int] = [1, 2, 3, 4, 5]

    def change_private(self):
        self._private_field = "PRIVATE_CHANGED"

    def get_private(self):
        return self._private_field


class DocumentWithTurnedOnStateManagement(Document):
    num_1: int
    num_2: int
    internal: InternalDoc

    class Settings:
        use_state_management = True


class DocumentWithTurnedOnStateManagementWithCustomId(Document):
    id: int
    num_1: int
    num_2: int

    class Settings:
        use_state_management = True


class DocumentWithTurnedOnReplaceObjects(Document):
    num_1: int
    num_2: int
    internal: InternalDoc

    class Settings:
        use_state_management = True
        state_management_replace_objects = True


class DocumentWithTurnedOnSavePrevious(Document):
    num_1: int
    num_2: int
    internal: InternalDoc

    class Settings:
        use_state_management = True
        state_management_save_previous = True


class DocumentWithTurnedOffStateManagement(Document):
    num_1: int
    num_2: int


class DocumentWithValidationOnSave(Document):
    num_1: int
    num_2: int
    related: PydanticObjectId = Field(default_factory=PydanticObjectId)

    @after_event(ValidateOnSave)
    def num_2_plus_1(self):
        self.num_2 += 1

    class Settings:
        validate_on_save = True
        use_state_management = True


class DocumentWithRevisionTurnedOn(Document):
    num_1: int
    num_2: int

    class Settings:
        use_revision = True
        use_state_management = True


class DocumentWithPydanticConfig(Document):
    if IS_PYDANTIC_V2:
        model_config = ConfigDict(validate_assignment=True)
    else:

        class Config:
            validate_assignment = True

    num_1: int


class DocumentWithExtras(Document):
    if IS_PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:

        class Config:
            extra = "allow"

    num_1: int


class DocumentWithExtrasKw(Document, extra="allow"):
    num_1: int


class Yard(Document):
    v: int
    w: int


class Lock(Document):
    k: int


class Window(Document):
    x: int
    y: int
    lock: Optional[Link[Lock]] = None


class WindowWithValidationOnSave(Document):
    x: int
    y: int
    lock: Optional[Link[Lock]] = None

    class Settings:
        validate_on_save = True


class Door(Document):
    t: int = 10
    window: Optional[Link[Window]] = None
    locks: Optional[List[Link[Lock]]] = None


class Roof(Document):
    r: int = 100


class House(Document):
    windows: List[Link[Window]]
    door: Link[Door]
    roof: Optional[Link[Roof]] = None
    yards: Optional[List[Link[Yard]]] = None
    height: Indexed(int) = 2
    name: Indexed(str) = Field(exclude=True)

    if IS_PYDANTIC_V2:
        model_config = ConfigDict(
            extra="allow",
        )
    else:

        class Config:
            extra = Extra.allow


class DocumentForEncodingTest(Document):
    bytes_field: Optional[bytes] = None
    datetime_field: Optional[datetime.datetime] = None


class DocumentWithTimeseries(Document):
    ts: datetime.datetime = Field(default_factory=datetime.datetime.now)

    class Settings:
        timeseries = TimeSeriesConfig(time_field="ts", expire_after_seconds=2)


class DocumentWithStringField(Document):
    string_field: str


class DocumentForEncodingTestDate(Document):
    date_field: datetime.date = Field(default_factory=datetime.date.today)


class DocumentUnion(UnionDoc):
    class Settings:
        name = "multi_model"
        class_id = "123"


class DocumentMultiModelOne(Document):
    int_filed: int = 0
    shared: int = 0

    class Settings:
        union_doc = DocumentUnion
        name = "multi_one"
        class_id = "123"


class DocumentMultiModelTwo(Document):
    str_filed: str = "test"
    shared: int = 0
    linked_doc: Optional[Link[DocumentMultiModelOne]] = None

    class Settings:
        union_doc = DocumentUnion
        name = "multi_two"
        class_id = "123"


class YardWithRevision(Document):
    v: int
    w: int

    class Settings:
        use_revision = True
        use_state_management = True


class LockWithRevision(Document):
    k: int

    class Settings:
        use_revision = True
        use_state_management = True


class WindowWithRevision(Document):
    x: int
    y: int
    lock: Link[LockWithRevision]

    class Settings:
        use_revision = True
        use_state_management = True


class HouseWithRevision(Document):
    windows: List[Link[WindowWithRevision]]

    class Settings:
        use_revision = True
        use_state_management = True


# classes for inheritance test
class Vehicle(Document):
    """Root parent for testing flat inheritance"""

    #               Vehicle
    #              /   |   \
    #             /    |    \
    #        Bicycle  Bike  Car
    #                         \
    #                          \
    #                          Bus
    color: str

    @after_event(Insert)
    def on_object_create(self):
        # this event will be triggered for all children too (self will have corresponding type)
        ...

    class Settings:
        is_root = True


class Bicycle(Vehicle):
    frame: int
    wheels: int


class Fuelled(BaseModel):
    """Just a mixin"""

    fuel: Optional[str] = None


class Car(Vehicle, Fuelled):
    body: str


class Bike(Vehicle, Fuelled):
    ...


class Bus(Car, Fuelled):
    seats: int


class Owner(Document):
    name: str
    vehicles: List[Link[Vehicle]] = []


class MixinNonRoot(BaseModel):
    id: int = Field(..., ge=1, le=254)


class MyDocNonRoot(Document):
    class Settings:
        use_state_management = True


class DocNonRoot(MixinNonRoot, MyDocNonRoot):
    name: str


class Doc2NonRoot(MyDocNonRoot):
    name: str


class Child(BaseModel):
    child_field: str


class SampleWithMutableObjects(Document):
    d: Dict[str, Child]
    lst: List[Child]


class SampleLazyParsing(Document):
    i: int
    s: str
    lst: List[int] = Field(
        [],
    )

    if IS_PYDANTIC_V2:
        model_config = ConfigDict(
            validate_assignment=True,
        )
    else:

        class Config:
            validate_assignment = True

    class Settings:
        lazy_parsing = True
        use_state_management = True


class RootDocument(Document):
    name: str
    link_root: Link[Document]


class ADocument(RootDocument):
    surname: str
    link_a: Link[Document]

    class Settings:
        name = "B"


class BDocument(RootDocument):
    email: str
    link_b: Link[Document]

    class Settings:
        name = "B"


class StateAndDecimalFieldModel(Document):
    amt: DecimalAnnotation
    other_amt: DecimalAnnotation = Field(
        decimal_places=1, multiple_of=0.5, default=0
    )

    class Settings:
        name = "amounts"
        use_revision = True
        use_state_management = True


class Region(Document):
    state: Optional[str] = "TEST"
    city: Optional[str] = "TEST"
    district: Optional[str] = "TEST"


class UsersAddresses(Document):
    region_id: Optional[Link[Region]] = None
    phone_number: Optional[str] = None
    street: Optional[str] = None


class AddressView(BaseModel):
    id: Optional[PydanticObjectId] = Field(alias="_id", default=None)
    phone_number: Optional[str] = None
    street: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None

    class Settings:
        projection = {
            "id": "$_id",
            "phone_number": 1,
            "street": 1,
            "sub_district": "$region_id.sub_district",
            "city": "$region_id.city",
            "state": "$region_id.state",
        }


class SelfLinked(Document):
    item: Optional[Link["SelfLinked"]] = None
    s: str

    class Settings:
        max_nesting_depth = 2


class LoopedLinksA(Document):
    b: Link["LoopedLinksB"]
    s: str

    class Settings:
        max_nesting_depths_per_field = {"b": 2}


class LoopedLinksB(Document):
    a: Optional[Link[LoopedLinksA]] = None
    s: str


class DocWithCollectionInnerClass(Document):
    s: str

    class Collection:
        name = "test"


class DocumentWithDecimalField(Document):
    amt: DecimalAnnotation
    other_amt: DecimalAnnotation = Field(
        decimal_places=1, multiple_of=0.5, default=0
    )

    if IS_PYDANTIC_V2:
        model_config = ConfigDict(
            validate_assignment=True,
        )
    else:

        class Config:
            validate_assignment = True

    class Settings:
        name = "amounts"
        use_revision = True
        use_state_management = True
        indexes = [
            pymongo.IndexModel(
                keys=[("amt", pymongo.ASCENDING)], name="amt_ascending"
            ),
            pymongo.IndexModel(
                keys=[("other_amt", pymongo.DESCENDING)],
                name="other_amt_descending",
            ),
        ]


class ModelWithOptionalField(BaseModel):
    s: Optional[str] = None
    i: int


class DocumentWithKeepNullsFalse(Document):
    o: Optional[str] = None
    m: ModelWithOptionalField

    class Settings:
        keep_nulls = False
        use_state_management = True


class ReleaseElemMatch(BaseModel):
    major_ver: int
    minor_ver: int
    build_ver: int


class PackageElemMatch(Document):
    releases: List[ReleaseElemMatch] = []


class DocumentWithLink(Document):
    link: Link["DocumentWithBackLink"]
    s: str = "TEST"


class DocumentWithBackLink(Document):
    if IS_PYDANTIC_V2:
        back_link: BackLink[DocumentWithLink] = Field(
            json_schema_extra={"original_field": "link"},
        )
    else:
        back_link: BackLink[DocumentWithLink] = Field(original_field="link")
    i: int = 1


class DocumentWithOptionalBackLink(Document):
    if IS_PYDANTIC_V2:
        back_link: Optional[BackLink[DocumentWithLink]] = Field(
            json_schema_extra={"original_field": "link"},
        )
    else:
        back_link: Optional[BackLink[DocumentWithLink]] = Field(
            original_field="link"
        )
    i: int = 1


class DocumentWithListLink(Document):
    link: List[Link["DocumentWithListBackLink"]]
    s: str = "TEST"


class DocumentWithListBackLink(Document):
    if IS_PYDANTIC_V2:
        back_link: List[BackLink[DocumentWithListLink]] = Field(
            json_schema_extra={"original_field": "link"},
        )
    else:
        back_link: List[BackLink[DocumentWithListLink]] = Field(
            original_field="link"
        )
    i: int = 1


class DocumentWithOptionalListBackLink(Document):
    if IS_PYDANTIC_V2:
        back_link: Optional[List[BackLink[DocumentWithListLink]]] = Field(
            json_schema_extra={"original_field": "link"},
        )
    else:
        back_link: Optional[List[BackLink[DocumentWithListLink]]] = Field(
            original_field="link"
        )
    i: int = 1


class DocumentWithUnionTypeExpressionOptionalBackLink(Document):
    if IS_PYDANTIC_V2:
        back_link_list: type_union(
            List[BackLink[DocumentWithListLink]], None
        ) = Field(json_schema_extra={"original_field": "link"})
        back_link: type_union(BackLink[DocumentWithLink], None) = Field(
            json_schema_extra={"original_field": "link"}
        )
    else:
        back_link_list: type_union(
            List[BackLink[DocumentWithListLink]], None
        ) = Field(original_field="link")
        back_link: type_union(BackLink[DocumentWithLink], None) = Field(
            original_field="link"
        )
    i: int = 1


class DocumentToBeLinked(Document):
    s: str = "TEST"


class DocumentWithListOfLinks(Document):
    links: List[Link[DocumentToBeLinked]]
    s: str = "TEST"


class DocumentWithTimeStampToTestConsistency(Document):
    ts: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class DocumentWithIndexMerging1(Document):
    class Settings:
        indexes = [
            "s1",
            [
                ("s2", pymongo.ASCENDING),
            ],
            IndexModel(
                [("s3", pymongo.ASCENDING)],
                name="s3_index",
            ),
            IndexModel(
                [("s4", pymongo.ASCENDING)],
                name="s4_index",
            ),
        ]


class DocumentWithIndexMerging2(DocumentWithIndexMerging1):
    class Settings:
        merge_indexes = True
        indexes = [
            "s0",
            "s1",
            [
                ("s2", pymongo.DESCENDING),
            ],
            IndexModel(
                [("s3", pymongo.DESCENDING)],
                name="s3_index",
            ),
        ]


class DocumentWithCustomInit(Document):
    s: ClassVar[str] = "TEST"

    @classmethod
    async def custom_init(cls):
        cls.s = "TEST2"


class LinkDocumentForTextSeacrh(Document):
    i: int


class DocumentWithTextIndexAndLink(Document):
    s: str
    link: Link[LinkDocumentForTextSeacrh]

    class Settings:
        indexes = [
            pymongo.IndexModel(
                [("s", pymongo.TEXT)],
                name="text_index",
            )
        ]


class DocumentWithList(Document):
    list_values: List[str]


class DocumentWithBsonBinaryField(Document):
    binary_field: BsonBinary


if IS_PYDANTIC_V2:
    Pets = RootModel[List[str]]
else:
    Pets = List[str]


class DocumentWithRootModelAsAField(Document):
    pets: Pets


class DocWithCallWrapper(Document):
    name: str

    if IS_PYDANTIC_V2:

        @validate_call
        def foo(self, bar: str) -> None:
            print(f"foo {bar}")


class DocumentWithHttpUrlField(Document):
    url_field: HttpUrl


class DocumentWithComplexDictKey(Document):
    dict_field: Dict[UUID, datetime.datetime]


class DocumentWithIndexedObjectId(Document):
    pyid: Indexed(PydanticObjectId)
    uuid: Annotated[UUID4, Indexed(unique=True)]
    email: Annotated[EmailStr, Indexed(unique=True)]


class DocumentToTestSync(Document):
    s: str = "TEST"
    i: int = 1
    n: Nested = Nested(
        integer=1, option_1=Option1(s="test"), union=Option1(s="test")
    )
    o: Optional[Option2] = None
    d: Dict[str, Any] = {}

    class Settings:
        use_state_management = True


class DocumentWithLinkForNesting(Document):
    link: Link["DocumentWithBackLinkForNesting"]
    s: str

    class Settings:
        max_nesting_depths_per_field = {"link": 0}


class DocumentWithBackLinkForNesting(Document):
    if IS_PYDANTIC_V2:
        back_link: BackLink[DocumentWithLinkForNesting] = Field(
            json_schema_extra={"original_field": "link"},
        )
    else:
        back_link: BackLink[DocumentWithLinkForNesting] = Field(
            original_field="link"
        )
    i: int

    class Settings:
        max_nesting_depths_per_field = {"back_link": 5}


class LongSelfLink(Document):
    link: Optional[Link["LongSelfLink"]] = None

    class Settings:
        max_nesting_depth = 50
