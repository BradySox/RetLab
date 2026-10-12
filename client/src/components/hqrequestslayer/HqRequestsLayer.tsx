import { selectCampaignStatus } from "../../api/campaignStatusSlice";
import { useAppSelector } from "../../app/hooks";
import { mapColors } from "../../theme/mapColors";
import { Circle, LayerGroup, Tooltip } from "react-leaflet";

// §112: a dashed ring round each target HQ has asked for. Sized in meters so it
// stays round the target at every zoom, and wide enough to find at theater zoom.
const RING_RADIUS_M = 9000;

export default function HqRequestsLayer() {
  const status = useAppSelector(selectCampaignStatus);
  const requests = status?.hq_requests ?? [];
  return (
    <LayerGroup>
      {requests.map((request) => (
        <Circle
          key={request.name}
          center={request.position}
          radius={RING_RADIUS_M}
          color={mapColors.hqRequest}
          weight={2}
          dashArray="6 6"
          fill={false}
        >
          <Tooltip>
            HQ request: {request.name} ({request.tier}, {request.turns_left} turn
            {request.turns_left === 1 ? "" : "s"} left)
          </Tooltip>
        </Circle>
      ))}
    </LayerGroup>
  );
}
