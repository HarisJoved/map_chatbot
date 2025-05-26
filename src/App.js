import React, { useState } from 'react';
import styled from 'styled-components';
import MapView from './components/MapView';
import ChatPanel from './components/ChatPanel';
import SearchBox from './components/SearchBox';

const AppContainer = styled.div`
  display: flex;
  width: 100%;
  height: 100vh;
  position: relative;
`;

const MapContainer = styled.div`
  flex-grow: 1;
  position: relative;
`;

function App() {
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [displayedLocations, setDisplayedLocations] = useState([]);
  const [viewState, setViewState] = useState({
    longitude: -122.41669,
    latitude: 37.7853,
    zoom: 13,
    pitch: 0,
    bearing: 0
  });

  // Track if we are currently showing multiple locations
  const [showingMultiple, setShowingMultiple] = useState(false);

  // Called when user selects a single location (e.g. from search box)
  const handleLocationSelect = (location) => {
    setSelectedLocation(location);
    // Only update displayedLocations if not showing multiple
    if (!showingMultiple) {
      setDisplayedLocations([location]);
    }
    setViewState({
      ...viewState,
      longitude: location.longitude,
      latitude: location.latitude,
      zoom: 14
    });
  };

  // Called when chatbot wants to show multiple locations
  const handleShowLocations = (locations) => {
    setDisplayedLocations(locations);
    setShowingMultiple(true);
    if (locations.length > 1) {
      const lons = locations.map(l => l.longitude);
      const lats = locations.map(l => l.latitude);
      const minLon = Math.min(...lons);
      const maxLon = Math.max(...lons);
      const minLat = Math.min(...lats);
      const maxLat = Math.max(...lats);
      setViewState(vs => ({
        ...vs,
        longitude: (minLon + maxLon) / 2,
        latitude: (minLat + maxLat) / 2,
        zoom: Math.min(14, Math.max(3, 12 - Math.log2(Math.max(maxLon-minLon, maxLat-minLat)+0.01)))
      }));
    } else if (locations.length === 1) {
      setViewState(vs => ({
        ...vs,
        longitude: locations[0].longitude,
        latitude: locations[0].latitude,
        zoom: 14
      }));
    }
  };

  return (
    <AppContainer>
      <ChatPanel onLocationSelect={handleLocationSelect} onShowLocations={handleShowLocations} />
      <MapContainer>
        <SearchBox onSearch={handleLocationSelect} />
        <MapView 
          viewState={viewState} 
          setViewState={setViewState}
          selectedLocation={selectedLocation}
          displayedLocations={displayedLocations}
        />
      </MapContainer>
    </AppContainer>
  );
}

export default App; 