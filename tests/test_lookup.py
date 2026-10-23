"""Explicit lookups isolate collections, even when IDs coincide."""

import pytest

from bibliotech import find_by_id


def test_find_by_id_returns_first_match():
    first = {"id": "same", "title": "first"}
    second = {"id": "same", "title": "second"}
    assert find_by_id([first, second], "same") is first


def test_find_by_id_returns_none_for_empty_or_missing():
    assert find_by_id([], "missing") is None
    assert find_by_id([{"id": "other"}], "missing") is None


@pytest.mark.parametrize(
    ("method", "collection"),
    [("find_book", "books"), ("find_member", "members"), ("find_loan", "loans")],
)
def test_lookup_uses_only_its_collection(library, method, collection):
    for name in ("books", "members", "loans"):
        getattr(library, name).append({"id": "same", "source": name})
    lookup = getattr(library, method)
    assert lookup("same")["source"] == collection
    assert lookup("missing") is None
