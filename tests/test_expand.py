"""Tests for FilterSet relationship expansion."""

import pytest
from sqlmodel import Field, Relationship, SQLModel

from fastapi_restkit import FilterSet, InvalidFormatError


class Owner(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    company_id: int | None = Field(default=None, foreign_key="company.id")


class Company(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    owner_id: int | None = Field(default=None, foreign_key="owner.id")
    owner: Owner = Relationship()
    users: list[User] = Relationship()


class CompanyFilterSet(FilterSet):
    class Config:
        expandable = {
            "owner": "owner",
            "users": "users",
        }
        default_expand = {"owner"}
        default_joined = {"owner"}


class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str
    internal_notes: str


class ProductFilterSet(FilterSet):
    class Config:
        column_fields = {
            "description": "description",
            "internal_notes": "internal_notes",
            "name": "name",
        }
        column_omit_mode = "defer"


class ProductLoadOnlyFilterSet(FilterSet):
    class Config:
        column_fields = {
            "description": "description",
            "internal_notes": "internal_notes",
            "name": "name",
        }
        column_omit_mode = "load_only"


def test_resolve_expands_defaults() -> None:
    filters = CompanyFilterSet()
    assert filters.resolve_expands() == {"owner"}


def test_resolve_expands_with_request() -> None:
    filters = CompanyFilterSet(expand=["users"])
    assert filters.resolve_expands() == {"owner", "users"}


def test_resolve_expands_with_omit() -> None:
    filters = CompanyFilterSet(omit=["owner"])
    assert filters.resolve_expands() == set()


def test_invalid_expand_raises() -> None:
    filters = CompanyFilterSet(expand=["invalid"])
    with pytest.raises(InvalidFormatError):
        filters.resolve_expands()


def test_load_options_generated() -> None:
    filters = CompanyFilterSet(expand=["users"])
    options = filters.to_sqlalchemy_load_options(Company)
    assert len(options) == 2


def test_column_omit_defer() -> None:
    filters = ProductFilterSet(omit=["description"])
    options = filters.to_sqlalchemy_column_options(Product)
    assert len(options) == 1


def test_column_omit_load_only() -> None:
    filters = ProductLoadOnlyFilterSet(omit=["description"])
    options = filters.to_sqlalchemy_column_options(Product)
    assert len(options) == 1


def test_only_limits_expands() -> None:
    filters = CompanyFilterSet(only=["users"])
    assert filters.resolve_expands() == {"users"}


def test_only_columns_load_only() -> None:
    filters = ProductFilterSet(only=["name"])
    options = filters.to_sqlalchemy_column_options(Product)
    assert len(options) == 1
