from typing import Dict, List
from uuid import UUID

from pydantic import BaseModel


class TransactionDetails(BaseModel):
    uuid: UUID
    transactionId: UUID
    transportCost: int
    alkuAmount: Dict[UUID, int]
    plates: List[str]
    informations: Dict[str, str]
