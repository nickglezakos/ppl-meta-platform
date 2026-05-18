from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(tags=["admin-ui"])

UI_ROOT = Path(__file__).resolve().parent.parent / "ui"
TEMPLATE_PATH = UI_ROOT / "templates" / "admin.html"
CONSOLE_TEMPLATE_PATH = UI_ROOT / "templates" / "console.html"
ASSETS_ROOT = UI_ROOT / "assets"
ASSET_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
}


@router.get("/admin", response_class=HTMLResponse)
async def admin_ui() -> HTMLResponse:
    if not TEMPLATE_PATH.exists():
        raise HTTPException(status_code=500, detail="Authority admin template is missing")

    return HTMLResponse(TEMPLATE_PATH.read_text(encoding="utf-8"))


@router.get("/admin/console", response_class=HTMLResponse)
async def admin_console_ui() -> HTMLResponse:
    if not CONSOLE_TEMPLATE_PATH.exists():
        raise HTTPException(status_code=500, detail="Authority console template is missing")

    return HTMLResponse(CONSOLE_TEMPLATE_PATH.read_text(encoding="utf-8"))


@router.get("/admin/assets/{asset_name}")
async def admin_asset(asset_name: str) -> FileResponse:
    asset_path = (ASSETS_ROOT / asset_name).resolve()
    if ASSETS_ROOT.resolve() not in asset_path.parents or not asset_path.exists() or not asset_path.is_file():
        raise HTTPException(status_code=404, detail="Authority admin asset not found")

    media_type = ASSET_CONTENT_TYPES.get(asset_path.suffix, "application/octet-stream")
    return FileResponse(asset_path, media_type=media_type)
