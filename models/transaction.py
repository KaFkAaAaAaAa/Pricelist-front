from typing import List
from uuid import UUID

from pydantic import BaseModel

from models.client import Client


class TransactionModel(BaseModel):
    uuid: UUID
    clientId: UUID | None
    client: Client | None
    description: str
    statusHistory: List
    itemsOrdered: List
    clientName: str | None
    clientAddress: str | None
