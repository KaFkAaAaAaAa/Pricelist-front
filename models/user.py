from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class User(BaseModel):
    userId: UUID
    userEmail: str
    userTelephoneNumber: str
    userFirstName: str
    userLastName: str
    userLastLogin: datetime | None
