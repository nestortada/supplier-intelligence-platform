from fastapi import APIRouter, Depends, HTTPException, status

from app.core.runtime_settings import RuntimeSettingsError, RuntimeSettingsService, get_runtime_settings_service


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/scoring")
def get_scoring_settings(
    settings_service: RuntimeSettingsService = Depends(get_runtime_settings_service),
) -> dict[str, float]:
    return settings_service.get_scoring()


@router.put("/scoring")
def update_scoring_settings(
    payload: dict[str, float],
    settings_service: RuntimeSettingsService = Depends(get_runtime_settings_service),
) -> dict[str, float]:
    try:
        return settings_service.update_scoring(payload)
    except RuntimeSettingsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/fees")
def get_fee_settings(
    settings_service: RuntimeSettingsService = Depends(get_runtime_settings_service),
) -> dict[str, float]:
    return settings_service.get_fees()


@router.put("/fees")
def update_fee_settings(
    payload: dict[str, float],
    settings_service: RuntimeSettingsService = Depends(get_runtime_settings_service),
) -> dict[str, float]:
    try:
        return settings_service.update_fees(payload)
    except RuntimeSettingsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
