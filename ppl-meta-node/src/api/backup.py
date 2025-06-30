import json
import os

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Response
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.backup_service import export_data, restore_data, backup_database, restore_database
from src.config import settings
from src.services.user_service import admin_required

router = APIRouter(prefix="/backup", tags=["backup"])

@router.get("/export", dependencies=[Depends(admin_required)])
def export_endpoint(db: Session = Depends(get_db)):
    data = export_data(db)
    return data

@router.get("/database", dependencies=[Depends(admin_required)])
def backup_db_endpoint(backup_path: str = "database_backup_path"):
    if backup_database(settings.DATABASE_URL, backup_path):
        with open(backup_path, "rb") as f:
            content = f.read()
        os.remove(backup_path)
        return Response(content, media_type="application/octet-stream", headers={
            "Content-Disposition": f"attachment; filename={backup_path}"
        })
    raise HTTPException(status_code=500, detail="Database backup failed")

@router.post("/restore", dependencies=[Depends(admin_required)])
async def restore_endpoint(
    db: Session = Depends(get_db),
    file: UploadFile = File(...)
):
    try:
        content = await file.read()
        data = json.loads(content)
        restore_data(db, data)
        return {"detail": "Restore completed successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Restore failed: {e}")

@router.post("/database", dependencies=[Depends(admin_required)])
async def restore_db_endpoint(file: UploadFile = File(...)):
    backup_path = "restore_upload_path"
    try:
        with open(backup_path, "wb") as f:
            f.write(await file.read())
        if restore_database(settings.DATABASE_URL, backup_path):
            os.remove(backup_path)
            return {"detail": "Database restored (previous DB backed up as .bak)."}
        raise HTTPException(status_code=500, detail="Database restore failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Restore failed: {e}")