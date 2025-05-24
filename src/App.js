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
  const [viewState, setViewState] = useState({
    longitude: -122.41669,
    latitude: 37.7853,
    zoom: 13,
    pitch: 0,
    bearing: 0
  });

  const handleLocationSelect = (location) => {
    setSelectedLocation(location);
    setViewState({
      ...viewState,
      longitude: location.longitude,
      latitude: location.latitude,
      zoom: 14
    });
  };

  return (
    <AppContainer>
      <ChatPanel onLocationSelect={handleLocationSelect} />
      <MapContainer>
        <SearchBox onSearch={handleLocationSelect} />
        <MapView 
          viewState={viewState} 
          setViewState={setViewState}
          selectedLocation={selectedLocation}
        />
      </MapContainer>
    </AppContainer>
  );
}

export default App; 