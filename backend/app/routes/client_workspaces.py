import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_active_organization, get_current_user
from app.models import Organization, User
from app.schemas.client_workspace import ClientWorkspaceCreate, ClientWorkspaceResponse, ClientWorkspaceUpdate
from app.services.client_workspace_service import archive_workspace, create_workspace, get_workspace, list_workspaces, update_workspace

router = APIRouter(prefix="/client-workspaces", tags=["client-workspaces"])

@router.get("", response_model=list[ClientWorkspaceResponse])
def index(db: Session = Depends(get_db), organization: Organization = Depends(get_active_organization)): return list_workspaces(db, organization)

@router.post("", response_model=ClientWorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create(payload: ClientWorkspaceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user), organization: Organization = Depends(get_active_organization)): return create_workspace(db, payload.name, payload.description, user, organization)

@router.get("/{workspace_id}", response_model=ClientWorkspaceResponse)
def show(workspace_id: uuid.UUID, db: Session = Depends(get_db), organization: Organization = Depends(get_active_organization)): return get_workspace(db, workspace_id, organization)

@router.patch("/{workspace_id}", response_model=ClientWorkspaceResponse)
def update(workspace_id: uuid.UUID, payload: ClientWorkspaceUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user), organization: Organization = Depends(get_active_organization)): return update_workspace(db, get_workspace(db, workspace_id, organization), payload.name, payload.description, user)

@router.post("/{workspace_id}/archive", response_model=ClientWorkspaceResponse)
def archive(workspace_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user), organization: Organization = Depends(get_active_organization)): return archive_workspace(db, get_workspace(db, workspace_id, organization), user)
