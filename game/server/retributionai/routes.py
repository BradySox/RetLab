"""REST transport for the outside AI: thin shims over ``game.agent.service``.

Every route needs the token (``?token=`` or ``X-API-Key``); the map server's own
routes do not, and stay as they were. Reads serialise with ``exclude_none``.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse

from game.agent import schemas, service, views
from game.server.security import ApiKeyManager

router: APIRouter = APIRouter(
    prefix="/retribution-ai", dependencies=[Depends(ApiKeyManager.verify)]
)


def _guarded(fn: Any, *args: Any) -> Any:
    try:
        return fn(*args)
    except (service.SideNotAllowedError, service.WritesOffError) as ex:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(ex))
    except RuntimeError as ex:  # GameContext.require with no campaign loaded
        raise HTTPException(status.HTTP_409_CONFLICT, str(ex))


@router.get("/start", operation_id="ai_start", response_class=PlainTextResponse)
def start(request: Request) -> str:
    return service.start_doc(str(request.base_url))


@router.get("/howtoplay", operation_id="ai_howtoplay", response_class=PlainTextResponse)
def howtoplay() -> str:
    return service.howtoplay_doc()


@router.get("/capabilities", operation_id="ai_capabilities")
def capabilities() -> dict[str, Any]:
    return service.capabilities()


@router.get(
    "/turn_context",
    operation_id="ai_turn_context",
    response_model=views.TurnContextView,
    response_model_exclude_none=True,
)
def turn_context(side: str = service.OPFOR_SIDE) -> views.TurnContextView:
    return _guarded(service.turn_context, side)


@router.get(
    "/settings",
    operation_id="ai_settings",
    response_model=views.SettingsView,
    response_model_exclude_none=True,
)
def settings() -> views.SettingsView:
    return _guarded(service.settings)


@router.get(
    "/packages",
    operation_id="ai_packages",
    response_model=list[views.PackageView],
    response_model_exclude_none=True,
)
def packages(side: str = service.OPFOR_SIDE) -> list[views.PackageView]:
    return _guarded(service.packages, side)


@router.get("/waypoints/{flight_id}", operation_id="ai_waypoints")
def waypoints(flight_id: str, side: str = service.OPFOR_SIDE) -> dict[str, Any]:
    return _guarded(service.waypoints, side, flight_id)


@router.get(
    "/ground/mine",
    operation_id="ai_own_sites",
    response_model=list[views.TargetView],
    response_model_exclude_none=True,
)
def own_sites(side: str = service.OPFOR_SIDE) -> list[views.TargetView]:
    """Red's own sites, with the ids its BARCAP packages aim at."""
    return _guarded(service.own_sites, side)


@router.get(
    "/iads",
    operation_id="ai_iads",
    response_model=views.IadsView,
    response_model_exclude_none=True,
)
def iads(side: str = service.OPFOR_SIDE) -> views.IadsView:
    return _guarded(service.iads, side)


@router.get(
    "/prev_turns",
    operation_id="ai_prev_turns",
    response_model=views.PrevTurnsView,
    response_model_exclude_none=True,
)
def prev_turns(n: int = 3) -> views.PrevTurnsView:
    return _guarded(service.prev_turns, n)


@router.get("/map/image", operation_id="ai_map_image")
def map_image(side: str = service.OPFOR_SIDE, bbox: Optional[str] = None) -> Response:
    """PNG strategic map; ``bbox`` is ``s,w,n,e`` in degrees."""
    png = _guarded(service.map_image, side, bbox)
    return Response(content=png, media_type="image/png")


@router.get("/human_notes", operation_id="ai_human_notes")
def human_notes() -> dict[str, str]:
    return _guarded(service.human_notes)


@router.get("/notes", operation_id="ai_notes")
def notes() -> dict[str, str]:
    """The AI's own notes, saved with the campaign."""
    return _guarded(service.notes)


@router.put("/notes", operation_id="ai_replace_notes")
def replace_notes(body: schemas.NotesRequest) -> dict[str, str]:
    return _guarded(service.replace_notes, body.notes)


@router.post("/notes", operation_id="ai_merge_notes")
def merge_notes(body: schemas.NotesRequest) -> dict[str, str]:
    return _guarded(service.merge_notes, body.notes)


@router.delete("/notes/{key}", operation_id="ai_delete_note")
def delete_note(key: str) -> dict[str, str]:
    return _guarded(service.delete_note, key)


@router.get(
    "/validate",
    operation_id="ai_validate",
    response_model=schemas.ValidateResult,
    response_model_exclude_none=True,
)
def validate(side: str = service.OPFOR_SIDE) -> schemas.ValidateResult:
    return _guarded(service.validate_plan, side)


@router.post(
    "/packages",
    operation_id="ai_create_packages",
    response_model=list[schemas.CreateResult],
    response_model_exclude_none=True,
)
def create_packages(body: schemas.CreatePackagesRequest) -> list[schemas.CreateResult]:
    return _guarded(service.create_packages, body.side, body.packages)


@router.post(
    "/packages/evaluate",
    operation_id="ai_evaluate_package",
    response_model=schemas.EvaluateResult,
    response_model_exclude_none=True,
)
def evaluate_package(body: schemas.EvaluatePackageRequest) -> schemas.EvaluateResult:
    return _guarded(service.evaluate_package, body.side, body.package)


@router.delete(
    "/packages",
    operation_id="ai_clear_packages",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def clear_packages(side: str = service.OPFOR_SIDE) -> schemas.OpResult:
    return _guarded(service.clear_packages, side)


@router.delete(
    "/packages/{index}",
    operation_id="ai_delete_package",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def delete_package(index: int, side: str = service.OPFOR_SIDE) -> schemas.OpResult:
    return _guarded(service.delete_package, side, index)


@router.post(
    "/packages/{index}/tot",
    operation_id="ai_set_package_tot",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def set_package_tot(index: int, body: schemas.PackageTotRequest) -> schemas.OpResult:
    return _guarded(service.set_package_tot, body.side, index, body.tot_minutes)


@router.post(
    "/stances",
    operation_id="ai_set_stance",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def set_stance(body: schemas.StanceRequest) -> schemas.OpResult:
    return _guarded(
        service.set_stance,
        body.side,
        body.friendly_cp_id,
        body.enemy_cp_id,
        body.stance,
    )


@router.post(
    "/buy/aircraft",
    operation_id="ai_buy_aircraft",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def buy_aircraft(body: schemas.BuyAircraftRequest) -> schemas.OpResult:
    return _guarded(service.buy_aircraft, body.side, body.squadron_id, body.quantity)


@router.post(
    "/sell/aircraft",
    operation_id="ai_sell_aircraft",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def sell_aircraft(body: schemas.BuyAircraftRequest) -> schemas.OpResult:
    return _guarded(service.sell_aircraft, body.side, body.squadron_id, body.quantity)


@router.post(
    "/buy/ground",
    operation_id="ai_buy_ground",
    response_model=schemas.OpResult,
    response_model_exclude_none=True,
)
def buy_ground(body: schemas.BuyGroundRequest) -> schemas.OpResult:
    return _guarded(
        service.buy_ground, body.side, body.cp_id, body.unit_name, body.quantity
    )
