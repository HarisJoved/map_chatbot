import React, { useState, useEffect } from 'react';
import Map, { Marker, Popup } from 'react-map-gl';
import { DeckGL, GeoJsonLayer } from 'deck.gl';
import styled from 'styled-components';
import maplibregl from 'maplibre-gl';
import RoomIcon from '@mui/icons-material/Room';
import parse from 'html-react-parser';

// Use OpenMapTiles Streets style
const MAPLIBRE_STYLE = 'https://tiles.stadiamaps.com/styles/alidade_smooth.json';

const MapContainer = styled.div`
  width: 100%;
  height: 100%;
  position: relative;
`;

const StyledDeck = styled(DeckGL)`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
`;

const ZoomControls = styled.div`
  position: absolute;
  bottom: 30px;
  right: 30px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 20;
`;

const ZoomButton = styled.button`
  width: 40px;
  height: 40px;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1.5rem;
  color: #01a3a4;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
  transition: background 0.2s, color 0.2s;
  &:hover {
    background: #01a3a4;
    color: #fff;
  }
`;

const PopupContent = styled.div`
  min-width: 180px;
`;
const PopupAddress = styled.div`
  font-weight: bold;
  color: #222;
`;
const PopupPostcode = styled.div`
  color: #666;
  font-size: 0.95em;
`;

const MapView = ({ viewState, setViewState, selectedLocation, displayedLocations = [] }) => {
  const [showPopup, setShowPopup] = useState(false);
  const [popupLocation, setPopupLocation] = useState(null);
  const [locationInfo, setLocationInfo] = useState(null);
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [errorInfo, setErrorInfo] = useState(null);

  useEffect(() => {
    setShowPopup(false);
    setLocationInfo(null);
    setErrorInfo(null);
    setPopupLocation(null);
  }, [displayedLocations]);

  // Simple example roads GeoJSON
  const roads = {
    type: 'FeatureCollection',
    features: [ /* ... your features ... */ ]
  };

  const roadLayer = new GeoJsonLayer({
    id: 'roads',
    data: roads,
    stroked: true,
    lineWidthMinPixels: 2,
    getLineColor: [160, 160, 180],
    getLineWidth: 5
  });

  const allLayers = [roadLayer];

  const handleZoomIn = () => setViewState(vs => ({ ...vs, zoom: Math.min((vs.zoom||0) +1, 20) }));
  const handleZoomOut = () => setViewState(vs => ({ ...vs, zoom: Math.max((vs.zoom||0) -1, 1) }));

  const handleMarkerClick = async (loc) => {
    setShowPopup(true);
    setPopupLocation(loc);
    setLoadingInfo(true);
    setErrorInfo(null);
    setLocationInfo(null);
    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: loc.address })
      });
      const data = await res.json();
      setLocationInfo(data.response);
    } catch {
      setErrorInfo('Failed to fetch location info.');
    } finally {
      setLoadingInfo(false);
    }
  };

  return (
    <MapContainer>
      <StyledDeck
        layers={allLayers}
        viewState={viewState}
        onViewStateChange={e => setViewState(e.viewState)}
        controller={true}
      >
        <Map
          mapLib={maplibregl}
          mapStyle={MAPLIBRE_STYLE}
        />
      </StyledDeck>
      {/* Single overlay Map for all markers */}
      <Map
        mapLib={maplibregl}
        mapStyle={MAPLIBRE_STYLE}
        interactive={false}
        viewState={viewState}
        style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}
      >
        {displayedLocations.map((loc, idx) => (
          <Marker
            key={loc.address + loc.postcode + idx}
            longitude={loc.longitude}
            latitude={loc.latitude}
            anchor="bottom"
          >
            <button
              onClick={() => handleMarkerClick(loc)}
              style={{
                background: 'none', border: 'none', padding: 0,
                margin: 0, cursor: 'pointer', outline: 'none',
                pointerEvents: 'auto'
              }}
              title="Show location info"
              aria-label="Show location info"
            >
              <RoomIcon style={{ fontSize: 36, color: '#d32f2f', filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.3))' }} />
            </button>
          </Marker>
        ))}
        {showPopup && popupLocation && (
          <Popup
            longitude={popupLocation.longitude}
            latitude={popupLocation.latitude}
            anchor="top"
            onClose={() => setShowPopup(false)}
            closeOnClick={false}
          >
            <PopupContent>
              <PopupAddress>{popupLocation.address}</PopupAddress>
              <PopupPostcode>{popupLocation.postcode}</PopupPostcode>
              {loadingInfo && <div>Loading info...</div>}
              {errorInfo && <div style={{ color: 'red' }}>{errorInfo}</div>}
              {locationInfo && <div>{parse(locationInfo)}</div>}
            </PopupContent>
          </Popup>
        )}
      </Map>
      <ZoomControls>
        <ZoomButton onClick={handleZoomIn} title="Zoom In">+</ZoomButton>
        <ZoomButton onClick={handleZoomOut} title="Zoom Out">-</ZoomButton>
      </ZoomControls>
    </MapContainer>
  );
};

export default MapView;
