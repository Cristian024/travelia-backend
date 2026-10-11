from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.packing import PackingItem, PackingList


class PackingItemResponse(BaseModel):
    position: int
    category: str
    item: str
    quantity: Optional[str] = None
    reason: Optional[str] = None
    checked: bool = False

    @classmethod
    def from_domain(cls, item: PackingItem, position: int) -> "PackingItemResponse":
        return cls(
            position=position,
            category=item.category,
            item=item.item,
            quantity=item.quantity,
            reason=item.reason,
            checked=item.checked,
        )


class PackingListResponse(BaseModel):
    id: str
    itinerary_id: str
    destination_summary: str
    weather_summary: str
    items: list[PackingItemResponse]
    notes: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, packing: PackingList) -> "PackingListResponse":
        return cls(
            id=packing.id,
            itinerary_id=packing.itinerary_id,
            destination_summary=packing.destination_summary,
            weather_summary=packing.weather_summary,
            items=[
                PackingItemResponse.from_domain(item, position)
                for position, item in enumerate(packing.items)
            ],
            notes=packing.notes,
            created_at=packing.created_at,
            updated_at=packing.updated_at,
        )


class SetPackingItemCheckedRequest(BaseModel):
    checked: bool
