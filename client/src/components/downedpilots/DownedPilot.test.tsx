import { DownedPilot as DownedPilotModel } from "../../api/liberationApi";
import { renderWithProviders } from "../../testutils";
import DownedPilot from "./DownedPilot";
import { LatLng } from "leaflet";
import { PropsWithChildren } from "react";

const mockMarker = jest.fn();
jest.mock("react-leaflet", () => ({
  Marker: (props: any) => {
    mockMarker(props);
    return <>{props.children}</>;
  },
  Tooltip: (props: PropsWithChildren<any>) => <>{props.children}</>,
}));

function pilot(blue: boolean): DownedPilotModel {
  return {
    id: "p1",
    name: "Maverick",
    squadron: "VF-1",
    aircraft: "F-14B",
    blue,
    position: new LatLng(0, 0),
    turns_remaining: 3,
    sidc: "",
  };
}

function lastMarkerProps() {
  const calls = mockMarker.mock.calls;
  return calls[calls.length - 1][0];
}

describe("DownedPilot", () => {
  beforeEach(() => mockMarker.mockClear());

  it("offers a rescue for our own pilot", () => {
    const { container } = renderWithProviders(
      <DownedPilot downedPilot={pilot(true)} />
    );
    expect(container.textContent).toContain("3 turns remaining to rescue");
    expect(container.textContent).toContain(
      "Right click to plan a CSAR mission"
    );
    expect(lastMarkerProps().eventHandlers.contextmenu).toBeDefined();
  });

  it("offers nothing for an enemy pilot", () => {
    const { container } = renderWithProviders(
      <DownedPilot downedPilot={pilot(false)} />
    );
    expect(container.textContent).toContain("Enemy rescue window: 3 turns");
    expect(container.textContent).not.toContain("CSAR mission");
    expect(container.textContent).not.toContain("remaining to rescue");
    expect(lastMarkerProps().eventHandlers.contextmenu).toBeUndefined();
  });
});
