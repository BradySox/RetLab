import { selectSectors, selectTerritory } from "../../api/territorySlice";
import { useAppSelector } from "../../app/hooks";
import { mapColors } from "../../theme/mapColors";
import "./TerritoryLayer.css";
import { divIcon, LatLngBounds, Map as LeafletMap } from "leaflet";
import { useState } from "react";
import {
  LayerGroup,
  Marker,
  Pane,
  Polygon,
  Polyline,
  useMap,
  useMapEvents,
} from "react-leaflet";

// §111: each side's whole ground as a see-through fill, with the front as the
// edge where the two meet. Its own pane under the default overlay pane (z 400),
// so every route, ring and icon draws on top of it.
export function TerritoryLayer() {
  const territory = useAppSelector(selectTerritory);
  return (
    <Pane name="territory" style={{ zIndex: 350 }}>
      <LayerGroup>
        {territory.blue.map((poly, idx) => (
          <Polygon
            key={`territory-blue-${idx}`}
            positions={poly}
            color={mapColors.territoryBlue}
            weight={1.5}
            fillColor={mapColors.territoryBlue}
            fillOpacity={0.28}
            interactive={false}
          />
        ))}
        {territory.red.map((poly, idx) => (
          <Polygon
            key={`territory-red-${idx}`}
            positions={poly}
            color={mapColors.territoryRed}
            weight={1.5}
            fillColor={mapColors.territoryRed}
            fillOpacity={0.28}
            interactive={false}
          />
        ))}
      </LayerGroup>
    </Pane>
  );
}

// Sector names are unreadable below this zoom; a thousand of them is clutter.
const SECTOR_LABEL_MIN_ZOOM = 9;

type MapView = { zoom: number; bounds: LatLngBounds };

// A map page loaded with the game already in place renders before the map has a
// center, and Leaflet throws on getBounds until it does (the map came back blank).
function currentView(map: LeafletMap): MapView | null {
  try {
    return { zoom: map.getZoom(), bounds: map.getBounds() };
  } catch {
    return null;
  }
}

// §111: the named sectors, about 10 NM across. Edges always; names only when
// zoomed in, and only those on screen.
export function SectorsLayer() {
  const sectors = useAppSelector(selectSectors);
  const map = useMap();
  const [view, setView] = useState<MapView | null>(() => currentView(map));
  useMapEvents({
    moveend: () => setView(currentView(map)),
  });
  const labels =
    view !== null && view.zoom >= SECTOR_LABEL_MIN_ZOOM
      ? sectors.sectors.filter((sector) => view.bounds.contains(sector.position))
      : [];
  return (
    <Pane name="sectors" style={{ zIndex: 360 }}>
      <LayerGroup>
        <Polyline
          positions={sectors.edges}
          color={mapColors.sectorEdge}
          weight={1}
          opacity={0.45}
          interactive={false}
        />
        {labels.map((sector) => (
          <Marker
            key={sector.name}
            position={sector.position}
            interactive={false}
            icon={divIcon({
              className: "sector-label",
              html: sector.name,
              iconSize: [96, 14],
              iconAnchor: [48, 7],
            })}
          />
        ))}
      </LayerGroup>
    </Pane>
  );
}
