from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.whop_webhook_service import receive_whop_webhook


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/whop")
async def whop_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    return await receive_whop_webhook(db, request)
