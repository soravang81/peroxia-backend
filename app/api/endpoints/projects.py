from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectWithMembersResponse, ProjectMemberCreate

router = APIRouter()

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_project = Project(
        name=project_in.name,
        description=project_in.description,
        owner_id=current_user.id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    # Automatically add owner as a member
    member = ProjectMember(project_id=new_project.id, user_id=current_user.id)
    db.add(member)
    db.commit()
    
    return new_project

@router.get("/", response_model=List[ProjectResponse])
def get_user_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Returns projects where the user is a member
    projects = db.query(Project).join(ProjectMember).filter(ProjectMember.user_id == current_user.id).all()
    return projects

@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED)
def add_project_member(project_id: int, member_in: ProjectMemberCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if current user is owner (authorization)
    if project.owner_id != current_user.id:
         raise HTTPException(status_code=403, detail="Not authorized to add members to this project")

    user_to_add = db.query(User).filter(User.id == member_in.user_id).first()
    if not user_to_add:
         raise HTTPException(status_code=404, detail="User not found")
         
    existing_member = db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == member_in.user_id).first()
    if existing_member:
         raise HTTPException(status_code=400, detail="User is already a member of this project")
         
    new_member = ProjectMember(project_id=project_id, user_id=member_in.user_id)
    db.add(new_member)
    db.commit()
    
    return {"message": "Member added successfully"}

@router.get("/{project_id}", response_model=ProjectWithMembersResponse)
def get_project_details(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
     project = db.query(Project).filter(Project.id == project_id).first()
     if not project:
          raise HTTPException(status_code=404, detail="Project not found")
          
     # Check if user is a member
     is_member = any(member.user_id == current_user.id for member in project.members)
     if not is_member:
          raise HTTPException(status_code=403, detail="Not a member of this project")
          
     return project
