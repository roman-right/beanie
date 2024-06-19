import dataclasses as dc
import datetime
import decimal
import enum
import ipaddress
import operator
import pathlib
import re
import uuid
from enum import Enum
from typing import (
    Any,
    Callable,
    Container,
    Iterable,
    Mapping,
    MutableMapping,
    Optional,
    Tuple,
)

import bson
import pydantic

import beanie
from beanie.odm.fields import Link, LinkTypes
from beanie.odm.utils.pydantic import IS_PYDANTIC_V2, get_model_fields

UNIX_TIME_START = datetime.datetime(1970, 1, 1, 0, 0, 0, 0)


def _compatct_time_encoder(time: datetime.time) -> str:
    # re-implementation of speed date in python
    # https://github.com/pydantic/speedate/blob/aad1d9117a05618ae883e20ae179c582eb998eeb /src/time.rs#L41 and
    # pydantic https://github.com/pydantic/pydantic-core/blob/f636403c2e8169bcbb94aa71a0727d76076f7e6e/src/input
    # /datetime.rs#L177
    if time.microsecond != 0:
        time_string = "{:02d}:{:02d}:{:02d}.{:06d}".format(
            time.hour, time.minute, time.second, time.microsecond
        )
    elif time.second != 0:
        time_string = "{:02d}:{:02d}:{:02d}".format(
            time.hour, time.minute, time.second
        )
    else:
        time_string = "{:02d}:{:02d}".format(time.hour, time.minute)

    tz_offset = None
    if time.tzinfo is not None:  # has timezone
        # check if the offset is fixed no matter the datetime
        offset_delta = time.tzinfo.utcoffset(None)
        if (
            offset_delta is None
        ):  # is ambiguous resolve base on 1.1.1970 to be consistent across time
            try:
                offset_delta = time.tzinfo.utcoffset(UNIX_TIME_START)
            except Exception as e:
                raise ValueError from e
            if offset_delta is not None:  # is not ambiguous
                tz_offset = round(offset_delta.total_seconds())
            else:  # even if stuffing time into may work is wrong see
                raise ValueError(
                    "timezone is not fixed and cannot be resolved with datetime,"
                    f"contact the maintainer of {type(time.tzinfo).__name__} for support"
                )
        else:  # is known without datetime
            tz_offset = round(offset_delta.total_seconds())

    if tz_offset is not None:
        if tz_offset == 0:
            time_string += "Z"
        else:
            is_negative = tz_offset < 0
            hours = abs(tz_offset // 3600)
            minutes = abs(tz_offset % 3600) // 60

            # since minutes are negative we need to subtract them from 60 and roll one hour back to be correct
            if is_negative and minutes != 0:
                hours -= 1
                minutes = 60 - minutes

            sign = "-" if is_negative else "+"
            time_string += "{}{:02d}:{:02d}".format(sign, hours, minutes)

    return time_string


SingleArgCallable = Callable[[Any], Any]
DEFAULT_CUSTOM_ENCODERS: MutableMapping[type, SingleArgCallable] = {
    ipaddress.IPv4Address: str,
    ipaddress.IPv4Interface: str,
    ipaddress.IPv4Network: str,
    ipaddress.IPv6Address: str,
    ipaddress.IPv6Interface: str,
    ipaddress.IPv6Network: str,
    pathlib.PurePath: str,
    pydantic.SecretBytes: pydantic.SecretBytes.get_secret_value,
    pydantic.SecretStr: pydantic.SecretStr.get_secret_value,
    # datetimes
    datetime.date: lambda d: datetime.datetime.combine(d, datetime.time.min),
    datetime.timedelta: operator.methodcaller("total_seconds"),
    datetime.time: _compatct_time_encoder,
    enum.Enum: operator.attrgetter("value"),
    Link: operator.attrgetter("ref"),
    bytes: bson.Binary,
    decimal.Decimal: bson.Decimal128,
    uuid.UUID: bson.Binary.from_uuid,
    re.Pattern: bson.Regex.from_native,
}
if IS_PYDANTIC_V2:
    from pydantic_core import Url

    DEFAULT_CUSTOM_ENCODERS[Url] = str

BSON_SCALAR_TYPES = (
    type(None),
    str,
    int,
    float,
    datetime.datetime,
    bson.Binary,
    bson.DBRef,
    bson.Decimal128,
    bson.MaxKey,
    bson.MinKey,
    bson.ObjectId,
)


@dc.dataclass
class Encoder:
    """
    BSON encoding class
    """

    exclude: Container[str] = frozenset()
    custom_encoders: Mapping[type, SingleArgCallable] = dc.field(
        default_factory=dict
    )
    to_db: bool = False
    keep_nulls: bool = True

    def _encode_document(self, obj: "beanie.Document") -> Mapping[str, Any]:
        obj.parse_store()
        settings = obj.get_settings()
        obj_dict = {}
        if settings.union_doc is not None:
            obj_dict[settings.class_id] = (
                settings.union_doc_alias or obj.__class__.__name__
            )
        if obj._class_id:
            obj_dict[settings.class_id] = obj._class_id

        link_fields = obj.get_link_fields() or {}
        sub_encoder = Encoder(
            # don't propagate self.exclude to subdocuments
            custom_encoders=settings.bson_encoders,
            to_db=self.to_db,
            keep_nulls=self.keep_nulls,
        )
        for key, value in self._iter_model_items(obj):
            if key in link_fields:
                link_type = link_fields[key].link_type
                if link_type in (LinkTypes.DIRECT, LinkTypes.OPTIONAL_DIRECT):
                    if value is not None:
                        value = value.to_ref()
                elif link_type in (LinkTypes.LIST, LinkTypes.OPTIONAL_LIST):
                    if value is not None:
                        value = [link.to_ref() for link in value]
                elif self.to_db:
                    continue
            obj_dict[key] = sub_encoder.encode(value)
        return obj_dict

    def encode(self, obj: Any) -> Any:
        if self.custom_encoders:
            encoder = _get_encoder(obj, self.custom_encoders)
            if encoder is not None:
                return encoder(obj)

        if isinstance(obj, BSON_SCALAR_TYPES):
            return obj

        encoder = _get_encoder(obj, DEFAULT_CUSTOM_ENCODERS)
        if encoder is not None:
            return encoder(obj)

        if isinstance(obj, beanie.Document):
            return self._encode_document(obj)
        if IS_PYDANTIC_V2 and isinstance(obj, pydantic.RootModel):
            return self.encode(obj.root)
        if isinstance(obj, pydantic.BaseModel):
            items = self._iter_model_items(obj)
            return {key: self.encode(value) for key, value in items}
        if isinstance(obj, Mapping):
            return {
                key if isinstance(key, Enum) else str(key): self.encode(value)
                for key, value in obj.items()
            }
        if isinstance(obj, Iterable):
            return [self.encode(value) for value in obj]

        raise ValueError(f"Cannot encode {obj!r}")

    def _iter_model_items(
        self, obj: pydantic.BaseModel
    ) -> Iterable[Tuple[str, Any]]:
        exclude, keep_nulls = self.exclude, self.keep_nulls
        get_model_field = get_model_fields(obj).get
        for key, value in obj.__iter__():
            field_info = get_model_field(key)
            if field_info is not None:
                key = field_info.alias or key
            if key not in exclude and (value is not None or keep_nulls):
                yield key, value


def _get_encoder(
    obj: Any, custom_encoders: Mapping[type, SingleArgCallable]
) -> Optional[SingleArgCallable]:
    encoder = custom_encoders.get(type(obj))
    if encoder is not None:
        return encoder
    for cls, encoder in custom_encoders.items():
        if isinstance(obj, cls):
            return encoder
    return None
