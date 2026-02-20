from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.core.websocket import manager
from app.db.session import get_db
from app.models.project import ProjectMember
from app.core.security import ALGORITHM
from app.core.config import settings
from jose import jwt, JWTError

router = APIRouter()

async def get_current_user_ws(token: str, db: Session):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        from app.models.user import User
        user = db.query(User).filter(User.username == username).first()
        return user
    except JWTError:
        return None

@router.websocket("/projects/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int, token: str, db: Session = Depends(get_db)):
    """
    WebSocket connection endpoint.
    Expects 'token' as a query parameter for authentication.
    """
    user = await get_current_user_ws(token, db)
    
    if not user:
        await websocket.close(code=1008, reason="Invalid credentials")
        return
        
    # Check if user is a member of the project
    is_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id, 
        ProjectMember.user_id == user.id
    ).first()
    
    if not is_member:
        from app.models.project import Project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project or project.owner_id != user.id:
            await websocket.close(code=1008, reason="Not authorized for this project room")
            return

    await manager.connect(websocket, project_id)
    try:
        while True:
            # We don't expect messages from client, but keeping it open to receive pings or handle disconnects
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
        print(f"Client disconnected from room {project_id}")
