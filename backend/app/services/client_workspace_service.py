import re
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import ClientWorkspace, Organization, User
from app.models.base import utc_now
from app.services.audit_service import create_audit_log

def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "client"

def get_workspace(db: Session, workspace_id: uuid.UUID, organization: Organization) -> ClientWorkspace:
    workspace = db.scalar(select(ClientWorkspace).where(ClientWorkspace.id == workspace_id, ClientWorkspace.organization_id == organization.id))
    if not workspace: raise HTTPException(status_code=404, detail="Client workspace not found.")
    return workspace

def list_workspaces(db: Session, organization: Organization) -> list[ClientWorkspace]:
    return list(db.scalars(select(ClientWorkspace).where(ClientWorkspace.organization_id == organization.id).order_by(ClientWorkspace.name)))

def create_workspace(db: Session, name: str, description: str | None, user: User, organization: Organization) -> ClientWorkspace:
    base = _slug(name); slug = base; suffix = 2
    while db.scalar(select(ClientWorkspace.id).where(ClientWorkspace.organization_id == organization.id, ClientWorkspace.slug == slug)):
        slug = f"{base}-{suffix}"; suffix += 1
    workspace = ClientWorkspace(organization_id=organization.id, name=name.strip(), slug=slug, description=description, created_by_user_id=user.id)
    db.add(workspace); db.flush()
    create_audit_log(db, organization_id=organization.id, workspace_id=workspace.id, user_id=user.id, action="client_workspace_created", entity_type="client_workspace", entity_id=workspace.id)
    db.commit(); db.refresh(workspace); return workspace

def update_workspace(db: Session, workspace: ClientWorkspace, name: str | None, description: str | None, user: User) -> ClientWorkspace:
    if name is not None: workspace.name = name.strip()
    if description is not None: workspace.description = description
    create_audit_log(db, organization_id=workspace.organization_id, workspace_id=workspace.id, user_id=user.id, action="client_workspace_updated", entity_type="client_workspace", entity_id=workspace.id)
    db.commit(); db.refresh(workspace); return workspace

def archive_workspace(db: Session, workspace: ClientWorkspace, user: User) -> ClientWorkspace:
    workspace.status = "archived"; workspace.archived_at = utc_now()
    create_audit_log(db, organization_id=workspace.organization_id, workspace_id=workspace.id, user_id=user.id, action="client_workspace_archived", entity_type="client_workspace", entity_id=workspace.id)
    db.commit(); db.refresh(workspace); return workspace
