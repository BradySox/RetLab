from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import (
    controlpoints,
    coordinates,
    debuggeometries,
    downedpilots,
    eventstream,
    flights,
    fogofwar,
    frontlines,
    game,
    maptiles,
    mapzones,
    navmesh,
    qt,
    retributionai,
    savedpoints,
    supplyroutes,
    tgos,
    waypoints,
    iadsnetwork,
)
from .security import ApiKeyManager
from .settings import ServerSettings

# The schema and its browser list every route; they are served keyed, below.
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# Every route needs a key. The map's routes serve blue's plan, so they take the map
# page's key and not the one the outside AI (§109) is handed for its own routes.
_MAP_KEY = [Depends(ApiKeyManager.verify_map)]
_AI_KEY = [Depends(ApiKeyManager.verify)]


@app.exception_handler(KeyError)
async def _key_error_as_404(request: Request, exc: KeyError) -> JSONResponse:
    """Unknown-id lookups raise KeyError, not None (Database.get,
    find_control_point_by_id), so the routes' `is None` guards never fire and a
    stale client id produced a 500 + traceback. Map them to a clean 404."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


app.include_router(controlpoints.router, dependencies=_MAP_KEY)
app.include_router(coordinates.router, dependencies=_MAP_KEY)
app.include_router(debuggeometries.router, dependencies=_MAP_KEY)
app.include_router(downedpilots.router, dependencies=_MAP_KEY)
app.include_router(
    eventstream.router, dependencies=[Depends(ApiKeyManager.verify_map_websocket)]
)
app.include_router(flights.router, dependencies=_MAP_KEY)
app.include_router(fogofwar.router, dependencies=_MAP_KEY)
app.include_router(frontlines.router, dependencies=_MAP_KEY)
app.include_router(game.router, dependencies=_MAP_KEY)
app.include_router(maptiles.router, dependencies=_MAP_KEY)
app.include_router(mapzones.router, dependencies=_MAP_KEY)
app.include_router(navmesh.router, dependencies=_MAP_KEY)
app.include_router(qt.router, dependencies=_MAP_KEY)
app.include_router(retributionai.router)  # keyed in its own module
app.include_router(savedpoints.router, dependencies=_MAP_KEY)
app.include_router(supplyroutes.router, dependencies=_MAP_KEY)
app.include_router(tgos.router, dependencies=_MAP_KEY)
app.include_router(waypoints.router, dependencies=_MAP_KEY)
app.include_router(iadsnetwork.router, dependencies=_MAP_KEY)


@app.get("/openapi.json", include_in_schema=False, dependencies=_AI_KEY)
def openapi_schema() -> dict[str, Any]:
    return app.openapi()


origins = ["file://"]
if ServerSettings.get().cors_allow_debug_server:
    origins.append("http://localhost:3000")


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
