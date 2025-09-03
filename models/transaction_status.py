from datetime import datetime

from pydantic import BaseModel

from enums.status import Status


class TransactionStatus(BaseModel):
    status: Status
    time: datetime
