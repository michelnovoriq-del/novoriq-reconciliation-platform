import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_active_organization, get_current_user
from app.models import Organization, User
from app.schemas.reconciliation_run import (
    ReconciliationRunCreate,
    ReconciliationRunResponse,
)
from app.schemas.match_result import ReconciliationResultsResponse
from app.services.matching_service import export_results, get_results, run_matching
from app.services.workbook_export_service import build_reconciliation_workbook, build_workbook_filename
from app.services.audit_service import create_audit_log
from app.services.reconciliation_service import (
    create_reconciliation_run,
    delete_reconciliation_run,
    get_reconciliation_run,
    list_reconciliation_runs,
)


router = APIRouter(prefix="/reconciliation-runs", tags=["reconciliation-runs"])


@router.post(
    "", response_model=ReconciliationRunResponse, status_code=status.HTTP_201_CREATED
)
def create_run(
    payload: ReconciliationRunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_active_organization),
):
    return create_reconciliation_run(
        db,
        file_a_id=payload.file_a_id,
        file_b_id=payload.file_b_id,
        workspace_id=payload.workspace_id,
        user=current_user,
        organization=organization,
    )


@router.get("", response_model=list[ReconciliationRunResponse])
def list_runs(
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_active_organization),
):
    return list_reconciliation_runs(db, organization)


@router.get("/{run_id}", response_model=ReconciliationRunResponse)
def get_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_active_organization),
):
    return get_reconciliation_run(db, run_id=run_id, organization=organization)


@router.post("/{run_id}/run", response_model=ReconciliationResultsResponse)
def execute_run(run_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), organization: Organization = Depends(get_active_organization)):
    run = get_reconciliation_run(db, run_id=run_id, organization=organization)
    return run_matching(db, run=run, user=current_user, organization=organization)


@router.get("/{run_id}/results", response_model=ReconciliationResultsResponse)
def reconciliation_results(run_id: uuid.UUID, db: Session = Depends(get_db), organization: Organization = Depends(get_active_organization)):
    return get_results(db, run_id=run_id, organization=organization)


@router.get("/{run_id}/export")
def export_run(run_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), organization: Organization = Depends(get_active_organization)):
    content = export_results(db, run_id=run_id, user=current_user, organization=organization)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="reconciliation_run_{run_id}.csv"'},
    )

@router.get("/{run_id}/export.xlsx")
def export_run_workbook(run_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), organization: Organization = Depends(get_active_organization)):
    run = get_reconciliation_run(db, run_id=run_id, organization=organization)
    content = build_reconciliation_workbook(db, run=run, organization=organization)
    create_audit_log(db, organization_id=organization.id, workspace_id=run.workspace_id, user_id=current_user.id, action="reconciliation_workbook_exported", entity_type="reconciliation_run", entity_id=run.id)
    db.commit()
    workspace = run.workspace.name if run.workspace_id and getattr(run, "workspace", None) else "Unassigned"
    filename = build_workbook_filename(db, run=run, workspace_name=workspace if workspace != "Unassigned" else None)
    return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), organization: Organization = Depends(get_active_organization)):
    delete_reconciliation_run(db, run_id=run_id, user=current_user, organization=organization)
