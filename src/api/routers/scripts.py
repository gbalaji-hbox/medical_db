from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response

from src.api.auth import get_current_identity

router = APIRouter(prefix="/api/scripts", tags=["scripts"])

_XHI_DIR = Path(__file__).resolve().parents[3] / "src" / "XHI" / "automation"


@router.get("/drchrono-submit.ts", response_class=PlainTextResponse)
def get_drchrono_script(identity: dict = Depends(get_current_identity)) -> str:
    return (_XHI_DIR / "drchrono-submit.ts").read_text(encoding="utf-8")


@router.get("/run_drchrono.bat")
def get_drchrono_bat(identity: dict = Depends(get_current_identity)) -> Response:
    content = (_XHI_DIR / "run_drchrono.bat").read_bytes()
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="run_drchrono.bat"'},
    )
