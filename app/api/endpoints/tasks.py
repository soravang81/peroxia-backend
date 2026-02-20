from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate, TaskStatusUpdate
from app.core.websocket import manager
import asyncio

router = APIRouter()

def check_project_membership(db: Session, project_id: int, user_id: int):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    is_member = db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="Not a member of this project")
    return project

async def simulate_send_email_notification(email: str, task_title: str):
    """
    Dummy background task simulating sending an email.
    """
    await asyncio.sleep(2)  # Simulate network latency
    print(f"\n[BACKGROUND JOB COMPLETED] Email successfully sent to '{email}' notifying assignment for task: '{task_title}'\n")

@router.get("/projects/{project_id}/tasks", response_model=List[TaskResponse])
def get_tasks(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_project_membership(db, project_id, current_user.id)
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    return tasks

@router.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(project_id: int, task_in: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_project_membership(db, project_id, current_user.id)
    
    new_task = Task(
        title=task_in.title,
        description=task_in.description,
        status=task_in.status,
        project_id=project_id,
        assignee_id=None # Default to unassigned, can add assignee_id in TaskCreate if needed
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Broadcast event
    await manager.broadcast({
        "event": "task_created",
        "data": {
            "id": new_task.id,
            "title": new_task.title,
            "status": new_task.status.value,
            "project_id": new_task.project_id
        }
    }, project_id)
    
    return new_task

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task_in: TaskUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    check_project_membership(db, task.project_id, current_user.id)

    # Check if a new assignee is being added to trigger the email
    trigger_email = False
    new_assignee_email = None
    if task_in.assignee_id and task_in.assignee_id != task.assignee_id:
        assignee = db.query(User).filter(User.id == task_in.assignee_id).first()
        if assignee:
            trigger_email = True
            new_assignee_email = assignee.email

    update_data = task_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
        
    db.commit()
    db.refresh(task)
    
    # Schedule background task
    if trigger_email and new_assignee_email:
        background_tasks.add_task(simulate_send_email_notification, new_assignee_email, task.title)
    
    # Broadcast event
    await manager.broadcast({
        "event": "task_updated",
        "data": {
            "id": task.id,
            "title": task.title,
            "status": task.status.value,
            "assignee_id": task.assignee_id
        }
    }, task.project_id)
    
    return task

@router.patch("/tasks/{task_id}/status", response_model=TaskResponse)
async def update_task_status(task_id: int, status_in: TaskStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    check_project_membership(db, task.project_id, current_user.id)

    task.status = status_in.status
    db.commit()
    db.refresh(task)
    
    # Broadcast event
    await manager.broadcast({
        "event": "status_changed",
        "data": {
            "id": task.id,
            "status": task.status.value
        }
    }, task.project_id)
    
    return task
