from pydantic import BaseModel

class RoleBase(BaseModel):
    name: str

class RoleCreate(RoleBase):
    pass

class RoleRead(RoleBase):
    id: int

    class Config:
        orm_mode = True

class UserRoleRead(BaseModel):
    id: int
    user_id: int
    role_id: int

    class Config:
        orm_mode = True

class RoleCapabilityCreate(BaseModel):
    role_id: int
    capability_id: int