from fastapi import APIRouter, HTTPException
from app.repositories import history as repo
from app.services import estimate_service
router = APIRouter()
@router.get("/runs")
def runs(limit: int = 50): return {"items": repo.list_runs(limit)}
@router.get("/runs/{run_id}")
def run_detail(run_id: int):
    r = repo.get_run(run_id)
    if not r:
        raise HTTPException(404, "run not found")
    return r
@router.post("/runs/{run_id}/recalc")
def run_recalc(run_id: int):
    return estimate_service.recalc_run(run_id)
