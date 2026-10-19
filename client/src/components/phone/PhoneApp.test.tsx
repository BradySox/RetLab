import { setupStore } from "../../app/store";
import { groupByPackage } from "./FlightsTab";
import PhoneApp from "./PhoneApp";
import { fireEvent, render, screen } from "@testing-library/react";
import { Provider } from "react-redux";

jest.mock("../liberationmap", () => ({
  __esModule: true,
  default: () => <div data-testid="map" />,
}));

const flight = (id: string, target: string, tot: string) => ({
  id,
  blue: true,
  sidc: "",
  package_target: target,
  package_tot: tot,
});

test("flights are grouped by package in TOT order", () => {
  const groups = groupByPackage([
    flight("a", "Bravo", "12:30"),
    flight("b", "Alpha", "12:10"),
    flight("c", "Bravo", "12:30"),
  ]);
  expect(groups.map((g) => g.target)).toEqual(["Alpha", "Bravo"]);
  expect(groups[1].flights.map((f) => f.id)).toEqual(["a", "c"]);
});

test("the tabs cover the map without unmounting it", () => {
  render(
    <Provider store={setupStore()}>
      <PhoneApp />
    </Provider>
  );
  fireEvent.click(screen.getByText("Flights"));
  expect(screen.getByText("No flights planned yet.")).toBeTruthy();
  expect(screen.getByTestId("map")).toBeTruthy();
  fireEvent.click(screen.getByText("Map"));
  expect(screen.queryByText("No flights planned yet.")).toBeNull();
});
