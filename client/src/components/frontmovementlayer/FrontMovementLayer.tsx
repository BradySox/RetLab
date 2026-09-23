import { FrontMovement } from "../../api/liberationApi";
import { selectFrontLines } from "../../api/frontLinesSlice";
import { useAppSelector } from "../../app/hooks";
import { mapColors } from "../../theme/mapColors";
import { LayerGroup, Polyline, Tooltip } from "react-leaflet";

function describe(movement: FrontMovement): string {
  const side = movement.advancing_side === "blue" ? "Blue" : "Red";
  return `${side} advanced ${movement.distance_nm.toFixed(1)} NM toward ${
    movement.toward
  } last turn`;
}

function MovementArrow(props: { movement: FrontMovement }) {
  const movement = props.movement;
  const color =
    movement.advancing_side === "blue" ? mapColors.friendly : mapColors.enemy;
  const parts = [movement.shaft, movement.head];
  return (
    <>
      {parts.map((positions, idx) => (
        <Polyline
          key={`casing-${idx}`}
          positions={positions}
          pathOptions={{ color: mapColors.strokeCasing, weight: 7 }}
          interactive={false}
        />
      ))}
      {parts.map((positions, idx) => (
        <Polyline
          key={`arrow-${idx}`}
          positions={positions}
          pathOptions={{ color: color, weight: 4 }}
        >
          <Tooltip sticky>
            {describe(movement)}
            {movement.blue_stance ? (
              <>
                <br />
                Blue stance: {movement.blue_stance}
              </>
            ) : null}
          </Tooltip>
        </Polyline>
      ))}
    </>
  );
}

// Last turn's front movement, one arrow per front that moved. Display only.
export default function FrontMovementLayer() {
  const fronts = useAppSelector(selectFrontLines).fronts;
  return (
    <LayerGroup>
      {Object.values(fronts).map((front) =>
        front.movement ? (
          <MovementArrow key={front.id} movement={front.movement} />
        ) : null
      )}
    </LayerGroup>
  );
}
