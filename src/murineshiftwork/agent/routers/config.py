from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/subjects")
def list_subjects(request: Request) -> dict:
    config_dir = Path(request.app.state.config_dir)
    subjects_dir = config_dir / "subjects"
    names = (
        sorted(p.stem for p in subjects_dir.glob("*.yaml"))
        if subjects_dir.exists()
        else []
    )
    return {"subjects": names}


@router.get("/setups")
def list_setups(request: Request) -> dict:
    config_dir = Path(request.app.state.config_dir)
    setups_dir = config_dir / "setups"
    names = (
        sorted(p.stem for p in setups_dir.glob("*.yaml")) if setups_dir.exists() else []
    )
    return {"setups": names}
