from pydantic import BaseModel

class NivelResponse(BaseModel):
    Id_Nivel: int
    Nivel: str
    class Config:
        orm_mode = True
