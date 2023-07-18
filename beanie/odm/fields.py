import asyncio
from collections import OrderedDict
from enum import Enum
from typing import (
    Dict,
    Generic,
    TypeVar,
    Union,
    Type,
    List,
    Optional,
    Any,
    TYPE_CHECKING, get_origin, get_args,
)

from typing import OrderedDict as OrderedDictType

from bson import ObjectId, DBRef
from bson.errors import InvalidId
from pydantic import BaseModel, parse_obj_as, GetCoreSchemaHandler, GetJsonSchemaHandler, TypeAdapter
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema, CoreSchema
from pydantic_core.core_schema import ValidatorFunctionWrapHandler, simple_ser_schema, ValidationInfo, str_schema
# from pydantic.json import ENCODERS_BY_TYPE
from pymongo import ASCENDING

from beanie.odm.enums import SortDirection
from beanie.odm.operators.find.comparison import (
    Eq,
    GT,
    GTE,
    LT,
    LTE,
    NE,
    In,
)
from beanie.odm.utils.parsing import parse_obj
from pymongo import IndexModel
from beanie.odm.registry import DocsRegistry

if TYPE_CHECKING:
    from beanie.odm.documents import DocType


def Indexed(typ, index_type=ASCENDING, **kwargs):
    """
    Returns a subclass of `typ` with an extra attribute `_indexed` as a tuple:
    - Index 0: `index_type` such as `pymongo.ASCENDING`
    - Index 1: `kwargs` passed to `IndexModel`
    When instantiated the type of the result will actually be `typ`.
    """

    class NewType(typ):
        _indexed = (index_type, kwargs)

        def __new__(cls, *args, **kwargs):
            return typ.__new__(typ, *args, **kwargs)

        @classmethod
        def __get_pydantic_core_schema__(
                cls, _source_type: Any, _handler: GetCoreSchemaHandler
        ) -> core_schema.CoreSchema:
            return core_schema.no_info_after_validator_function(
                lambda v: v,
                simple_ser_schema(typ.__name__),
            )

    NewType.__name__ = f"Indexed {typ.__name__}"
    return NewType


class PydanticObjectId(ObjectId):
    """
    Object Id field. Compatible with Pydantic.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, _: ValidationInfo):
        if isinstance(v, bytes):
            v = v.decode("utf-8")
        try:
            return PydanticObjectId(v)
        except InvalidId:
            raise ValueError("Id must be of type PydanticObjectId")

    # @classmethod
    # def __modify_schema__(cls, field_schema):
    #     field_schema.update(
    #         type="string",
    #         examples=["5eb7cf5a86d9755df3a6c593", "5eb7cfb05e32e07750a1756a"],
    #     )

    @classmethod
    def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.json_or_python_schema(
            python_schema=core_schema.general_plain_validator_function(cls.validate),
            json_schema=str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: str(instance)
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
            cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(schema)
        json_schema.update(
            type="string",
            examples=["5eb7cf5a86d9755df3a6c593", "5eb7cfb05e32e07750a1756a"],
        )
        return json_schema


# ENCODERS_BY_TYPE[
#     PydanticObjectId
# ] = str  # it is a workaround to force pydantic make json schema for this field


class ExpressionField(str):
    def __getitem__(self, item):
        """
        Get sub field

        :param item: name of the subfield
        :return: ExpressionField
        """
        return ExpressionField(f"{self}.{item}")

    def __getattr__(self, item):
        """
        Get sub field

        :param item: name of the subfield
        :return: ExpressionField
        """
        return ExpressionField(f"{self}.{item}")

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if isinstance(other, ExpressionField):
            return super(ExpressionField, self).__eq__(other)
        return Eq(field=self, other=other)

    def __gt__(self, other):
        return GT(field=self, other=other)

    def __ge__(self, other):
        return GTE(field=self, other=other)

    def __lt__(self, other):
        return LT(field=self, other=other)

    def __le__(self, other):
        return LTE(field=self, other=other)

    def __ne__(self, other):
        return NE(field=self, other=other)

    def __pos__(self):
        return self, SortDirection.ASCENDING

    def __neg__(self):
        return self, SortDirection.DESCENDING

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self


class DeleteRules(str, Enum):
    DO_NOTHING = "DO_NOTHING"
    DELETE_LINKS = "DELETE_LINKS"


class WriteRules(str, Enum):
    DO_NOTHING = "DO_NOTHING"
    WRITE = "WRITE"


class LinkTypes(str, Enum):
    DIRECT = "DIRECT"
    OPTIONAL_DIRECT = "OPTIONAL_DIRECT"
    LIST = "LIST"
    OPTIONAL_LIST = "OPTIONAL_LIST"

    BACK_DIRECT = "BACK_DIRECT"
    BACK_LIST = "BACK_LIST"
    OPTIONAL_BACK_DIRECT = "OPTIONAL_BACK_DIRECT"
    OPTIONAL_BACK_LIST = "OPTIONAL_BACK_LIST"


class LinkInfo(BaseModel):
    field_name: str
    lookup_field_name: str
    document_class: Type[BaseModel]  # Document class
    link_type: LinkTypes
    nested_links: Optional[Dict] = None


T = TypeVar("T")


class Link(Generic[T]):
    def __init__(self, ref: DBRef, document_class: Type[T]):
        self.ref = ref
        self.document_class = document_class

    async def fetch(self, fetch_links: bool = False) -> Union[T, "Link"]:
        result = await self.document_class.get(  # type: ignore
            self.ref.id, with_children=True, fetch_links=fetch_links
        )
        return result or self

    @classmethod
    async def fetch_one(cls, link: "Link"):
        return await link.fetch()

    @classmethod
    async def fetch_list(
            cls, links: List[Union["Link", "DocType"]], fetch_links: bool = False
    ):
        """
        Fetch list that contains links and documents
        :param links:
        :param fetch_links:
        :return:
        """
        data = Link.repack_links(links)  # type: ignore
        ids_to_fetch = []
        document_class = None
        for doc_id, link in data.items():
            if isinstance(link, Link):
                if document_class is None:
                    document_class = link.document_class
                else:
                    if document_class != link.document_class:
                        raise ValueError(
                            "All the links must have the same model class"
                        )
                ids_to_fetch.append(link.ref.id)

        fetched_models = await document_class.find(  # type: ignore
            In("_id", ids_to_fetch),
            with_children=True,
            fetch_links=fetch_links,
        ).to_list()

        for model in fetched_models:
            data[model.id] = model

        return list(data.values())

    @staticmethod
    def repack_links(
            links: List[Union["Link", "DocType"]]
    ) -> OrderedDictType[Any, Any]:
        result = OrderedDict()
        for link in links:
            if isinstance(link, Link):
                result[link.ref.id] = link
            else:
                result[link.id] = link
        return result

    @classmethod
    async def fetch_many(cls, links: List["Link"]):
        coros = []
        for link in links:
            coros.append(link.fetch())
        return await asyncio.gather(*coros)

    # @classmethod
    # def __get_validators__(cls):
    #     yield cls.validate

    @classmethod
    def build_validation(cls, handler, source_type):

        def validate(v: Union[DBRef, T], validation_info: ValidationInfo):
            document_class = DocsRegistry.evaluate_fr(get_args(source_type)[0])  # type: ignore

            if isinstance(v, DBRef):
                return cls(ref=v, document_class=document_class)
            if isinstance(v, Link):
                return v
            if isinstance(v, dict) or isinstance(v, BaseModel):
                return parse_obj(document_class, v)
            new_id = TypeAdapter(document_class.model_fields["id"].annotation).validate_python(v)
            ref = DBRef(collection=document_class.get_collection_name(), id=new_id)
            return cls(ref=ref, document_class=document_class)

        return validate

    def to_ref(self):
        return self.ref

    def to_dict(self):
        return {"id": str(self.ref.id), "collection": self.ref.collection}

    @staticmethod
    def serialize(value: Union["Link", BaseModel]):
        if isinstance(value, Link):
            return value.to_dict()
        return value.model_dump()

    @classmethod
    def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.json_or_python_schema(
            python_schema=core_schema.general_plain_validator_function(cls.build_validation(handler, source_type)),
            json_schema=core_schema.typed_dict_schema(
                        {
                            'id': core_schema.typed_dict_field(
                                core_schema.str_schema()
                            ),
                            'collection': core_schema.typed_dict_field(core_schema.str_schema()),
                        }
                    ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: cls.serialize(instance)
            ),
        )
        return core_schema.general_plain_validator_function(cls.build_validation(handler, source_type))


# ENCODERS_BY_TYPE[Link] = lambda o: o.to_dict()


class BackLink(Generic[T]):
    """Back reference to a document"""

    def __init__(self, document_class: Type[T]):
        self.document_class = document_class

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def build_validation(cls, handler, source_type):

        def validate(v: Union[DBRef, T], field):
            document_class = get_args(source_type)[0]  # type: ignore
            if isinstance(v, dict) or isinstance(v, BaseModel):
                return parse_obj(document_class, v)
            return cls(document_class=document_class)
        return validate

    def to_dict(self):
        return {"collection": self.document_class.get_collection_name()}

    @classmethod
    def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.general_plain_validator_function(cls.build_validation(handler, source_type))


# ENCODERS_BY_TYPE[BackLink] = lambda o: o.to_dict()


class IndexModelField:
    def __init__(self, index: IndexModel):
        self.index = index
        self.name = index.document["name"]

        self.fields = tuple(sorted(self.index.document["key"]))
        self.options = tuple(
            sorted(
                (k, v)
                for k, v in self.index.document.items()
                if k not in ["key", "v"]
            )
        )

    def __eq__(self, other):
        return self.fields == other.fields and self.options == other.options

    def __repr__(self):
        return f"IndexModelField({self.name}, {self.fields}, {self.options})"

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, *args, **kwargs):
        if isinstance(v, IndexModel):
            return IndexModelField(v)
        else:
            return IndexModelField(IndexModel(v))

    @staticmethod
    def list_difference(
            left: List["IndexModelField"], right: List["IndexModelField"]
    ):
        result = []
        for index in left:
            if index not in right:
                result.append(index)
        return result

    @staticmethod
    def list_to_index_model(left: List["IndexModelField"]):
        return [index.index for index in left]

    @classmethod
    def from_motor_index_information(cls, index_info: dict):
        result = []
        for name, details in index_info.items():
            fields = details["key"]
            if ("_id", 1) in fields:
                continue

            options = {k: v for k, v in details.items() if k != "key"}
            index_model = IndexModelField(
                IndexModel(fields, name=name, **options)
            )
            result.append(index_model)
        return result

    def same_fields(self, other: "IndexModelField"):
        return self.fields == other.fields

    @staticmethod
    def find_index_with_the_same_fields(
            indexes: List["IndexModelField"], index: "IndexModelField"
    ):
        for i in indexes:
            if i.same_fields(index):
                return i
        return None

    @staticmethod
    def merge_indexes(
            left: List["IndexModelField"], right: List["IndexModelField"]
    ):
        left_dict = {index.fields: index for index in left}
        right_dict = {index.fields: index for index in right}
        left_dict.update(right_dict)
        return list(left_dict.values())

    @classmethod
    def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.general_plain_validator_function(cls.validate)
