from pydantic import BaseModel
from typing import List, Optional
from app.schemas.user import UserResponse

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    owner_id: int

    class Config:
        from_attributes = True

class ProjectWithMembersResponse(ProjectResponse):
    members: List["ProjectMemberResponse"] = []

class ProjectMemberCreate(BaseModel):
    user_id: int

class ProjectMemberResponse(BaseModel):
    project_id: int
    user_id: int
    user: UserResponse

    class Config:
        from_attributes = True
