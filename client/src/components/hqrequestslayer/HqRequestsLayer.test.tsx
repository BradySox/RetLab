import { renderWithProviders } from "../../testutils";
import HqRequestsLayer from "./HqRequestsLayer";
import { PropsWithChildren } from "react";

const mockCircle = jest.fn();
jest.mock("react-leaflet", () => ({
  LayerGroup: (props: PropsWithChildren<any>) => <>{props.children}</>,
  Circle: (props: PropsWithChildren<any>) => {
    mockCircle(props);
    return null;
  },
  Tooltip: (props: PropsWithChildren<any>) => <>{props.children}</>,
}));

const status = {
  turn: 3,
  date: "2026-10-12",
  hq_requests: [
    {
      name: "Rail yard",
      kind: "Warehouse",
      base: "Sukhumi",
      tier: "easy",
      turns_left: 2,
      why: "",
      position: { lat: 43, lng: 41 },
    },
    {
      name: "SA-11",
      kind: "AA Defense Site",
      base: "Gudauta",
      tier: "hard",
      turns_left: 1,
      why: "",
      position: { lat: 43.1, lng: 40.6 },
    },
  ],
};

describe("HqRequestsLayer", () => {
  beforeEach(() => mockCircle.mockClear());

  it("rings every request", () => {
    renderWithProviders(<HqRequestsLayer />, {
      preloadedState: { campaignStatus: { status: status } },
    });
    expect(mockCircle).toHaveBeenCalledTimes(2);
    expect(mockCircle.mock.calls[0][0].center).toEqual({ lat: 43, lng: 41 });
  });

  it("draws nothing without a game", () => {
    renderWithProviders(<HqRequestsLayer />, {
      preloadedState: { campaignStatus: { status: null } },
    });
    expect(mockCircle).not.toHaveBeenCalled();
  });
});
