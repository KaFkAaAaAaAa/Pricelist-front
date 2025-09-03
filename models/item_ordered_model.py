from uuid import UUID

from pydantic import BaseModel


class ItemOrderedModel(BaseModel):
    uuid: UUID
    sku: str
    accountingNumber: str | None
    name: str
    price: str
    amount: int
    additionalInfo: str
    transactionId: UUID
    isItemNew: bool
