from typing import Any, Callable, Coroutine

from typing_extensions import Protocol, TypeAlias, assert_type

from beanie import Document
from beanie.odm.actions import EventTypes, wrap_with_actions
from beanie.odm.utils.self_validation import validate_self_before
from beanie.odm.utils.state import (
    previous_saved_state_needed,
    save_state_after,
    saved_state_needed,
)


def sync_func(doc_self: Document, arg1: str, arg2: int, /) -> Document:
    """
    Models `Document` sync method that expects self
    """
    raise NotImplementedError


SyncFunc: TypeAlias = Callable[[Document, str, int], Document]


async def async_func(doc_self: Document, arg1: str, arg2: int, /) -> Document:
    """
    Models `Document` async method that expects self
    """
    raise NotImplementedError


AsyncFunc: TypeAlias = Callable[
    [Document, str, int], Coroutine[Any, Any, Document]
]


def test_wrap_with_actions_preserves_signature() -> None:
    assert_type(async_func, AsyncFunc)
    assert_type(wrap_with_actions(EventTypes.SAVE)(async_func), AsyncFunc)


def test_save_state_after_preserves_signature() -> None:
    assert_type(async_func, AsyncFunc)
    assert_type(save_state_after(async_func), AsyncFunc)


def test_validate_self_before_preserves_signature() -> None:
    assert_type(async_func, AsyncFunc)
    assert_type(validate_self_before(async_func), AsyncFunc)


def test_saved_state_needed_preserves_signature() -> None:
    assert_type(async_func, AsyncFunc)
    assert_type(saved_state_needed(async_func), AsyncFunc)

    assert_type(sync_func, SyncFunc)
    assert_type(saved_state_needed(sync_func), SyncFunc)


def test_previous_saved_state_needed_preserves_signature() -> None:
    assert_type(async_func, AsyncFunc)
    assert_type(previous_saved_state_needed(async_func), AsyncFunc)

    assert_type(sync_func, SyncFunc)
    assert_type(previous_saved_state_needed(sync_func), SyncFunc)


class ExpectsDocumentSelf(Protocol):
    def __call__(self, doc_self: Document, /) -> Any: ...


def test_document_insert_expects_self() -> None:
    test_insert: ExpectsDocumentSelf = Document.insert  # noqa: F841


def test_document_save_expects_self() -> None:
    test_insert: ExpectsDocumentSelf = Document.save  # noqa: F841


def test_document_replace_expects_self() -> None:
    test_insert: ExpectsDocumentSelf = Document.replace  # noqa: F841
