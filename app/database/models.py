"""Модели данных (dataclasses для типизации)."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ListingType(str, Enum):
    RENT = "rent"
    SALE = "sale"


class Plan(str, Enum):
    TRIAL = "trial"
    PAID = "paid"


@dataclass
class User:
    id: int
    username: str | None
    first_name: str | None
    created_at: datetime
    notifications_enabled: bool
    rent_enabled: bool
    sale_enabled: bool


@dataclass
class Subscription:
    id: int
    user_id: int
    plan: str
    started_at: datetime
    expires_at: datetime | None


@dataclass
class Listing:
    id: int
    external_id: str
    source: str
    type: str
    title: str | None
    url: str | None
    price: int | None
    raw_data: dict | None
    created_at: datetime


@dataclass
class UserFilter:
    id: int
    user_id: int
    listing_type: str
    city: str | None
    min_price: int | None
    max_price: int | None
    created_at: datetime
