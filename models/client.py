from uuid import UUID

from pydantic import BaseModel


class Client(BaseModel):
    user: User
    clientCompanyName: str
    clientStreet: str
    clientCode: str
    clientCity: str
    clientCountry: str
    clientAdminId: UUID
    private String clientCompanyName;
    // address
    private String clientStreet;
    private String clientCode;
    private String clientCity;
    private String clientCountry;
    @ManyToOne(fetch = FetchType.EAGER, optional = true)
    @Fetch(FetchMode.SELECT)
    private User clientAdmin;
