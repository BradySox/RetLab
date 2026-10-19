import CampaignStatusBar from "./components/campaignstatus";
import EventsFeed from "./components/eventsfeed";
import MapLegend from "./components/legend/MapLegend";
import LiberationMap from "./components/liberationmap";
import PhoneApp from "./components/phone/PhoneApp";
import usePhoneLayout from "./components/phone/usePhoneLayout";
import useEventStream from "./hooks/useEventSteam";
import useInitialGameState from "./hooks/useInitialGameState";

function App() {
  useInitialGameState();
  useEventStream();
  const phone = usePhoneLayout();

  if (phone) {
    return <PhoneApp />;
  }
  return (
    <div className="App">
      <CampaignStatusBar />
      <EventsFeed />
      <MapLegend />
      <LiberationMap />
    </div>
  );
}

export default App;
