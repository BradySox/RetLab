"""REST transport for the outside AI: thin shims over ``game.agent.service``.

Every route needs the token (``?token=`` or ``X-API-Key``); the map server's own
routes do not, and stay as they were. Reads serialise with ``exclude_none``.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse

from game.agent import service, views
from game.server.security import ApiKeyManager

router: APIRouter = APIRouter(
    prefix="/retribution-ai", dependencies=[Depends(ApiKeyManager.verify)]
)


def _guarded(fn: Any, *args: Any) -> Any:
    try:
        return fn(*args)
    except service.SideNotAllowedError as ex:
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
