import { RootState } from "../app/store";
import { gameLoaded, gameUnloaded } from "./actions";
import { Sectors, Territory } from "./liberationApi";
import { createSlice } from "@reduxjs/toolkit";

// §111: each side's ground and the named sectors it is cut into. Fed by the
// /game payload. Display only; never fogged, since it follows from the bases
// and fronts the map already shows.
interface TerritoryState {
  territory: Territory;
  sectors: Sectors;
}

const initialState: TerritoryState = {
  territory: { blue: [], red: [] },
  sectors: { edges: [], sectors: [] },
};

const territorySlice = createSlice({
  name: "territory",
  initialState: initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(gameLoaded, (state, action) => {
      state.territory = action.payload.territory ?? initialState.territory;
      state.sectors = action.payload.sectors ?? initialState.sectors;
    });
    builder.addCase(gameUnloaded, (state) => {
      state.territory = initialState.territory;
      state.sectors = initialState.sectors;
    });
  },
});

export const selectTerritory = (state: RootState) => state.territory.territory;
export const selectSectors = (state: RootState) => state.territory.sectors;

export default territorySlice.reducer;
