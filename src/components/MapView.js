import React, { useState, useEffect } from 'react';
import Map, { Marker, Popup } from 'react-map-gl';
import { DeckGL, ScatterplotLayer, GeoJsonLayer } from 'deck.gl';
import styled from 'styled-components';
import maplibregl from 'maplibre-gl';

// Use OpenMapTiles Streets style for more details
const MAPLIBRE_STYLE = 'https://tiles.stadiamaps.com/styles/alidade_smooth.json';

const MapContainer = styled.div`
  width: 100%;
  height: 100%;
  position: relative;
`;

const CustomMarker = styled.div`
  width: 20px;
  height: 20px;
  background-color: #01a3a4;
  border-radius: 50%;
  border: 2px solid white;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
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

const MapView = ({ viewState, setViewState, selectedLocation }) => {
  const [layers, setLayers] = useState([]);
  const [showPopup, setShowPopup] = useState(true);

  useEffect(() => {
    if (selectedLocation) {
      setShowPopup(true);
      const newLayers = [
        new ScatterplotLayer({
          id: 'selected-location',
          data: [selectedLocation],
          pickable: true,
          opacity: 0.8,
          stroked: true,
          filled: true,
          radiusScale: 10,
          radiusMinPixels: 10,
          radiusMaxPixels: 100,
          lineWidthMinPixels: 1,
          getPosition: d => [d.longitude, d.latitude],
          getRadius: d => 500,
          getFillColor: [1, 163, 164, 140],
          getLineColor: [1, 163, 164]
        })
      ];
      setLayers(newLayers);
    } else {
      setLayers([]);
      setShowPopup(false);
    }
  }, [selectedLocation]);

  // Example GeoJSON data for roads (simplified)
  const roads = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [-122.41, 37.78],
            [-122.42, 37.79],
            [-122.43, 37.78]
          ]
        },
        properties: {
          name: 'Main Ave'
        }
      },
      {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [-122.41, 37.78],
            [-122.40, 37.77]
          ]
        },
        properties: {
          name: 'North Ave'
        }
      }
    ]
  };

  const roadLayer = new GeoJsonLayer({
    id: 'roads',
    data: roads,
    stroked: true,
    lineWidthMinPixels: 2,
    getLineColor: [160, 160, 180],
    getLineWidth: 5
  });

  const allLayers = [...layers, roadLayer];

  const handleZoomIn = () => {
    setViewState(vs => ({ ...vs, zoom: Math.min((vs.zoom || 0) + 1, 20) }));
  };
  const handleZoomOut = () => {
    setViewState(vs => ({ ...vs, zoom: Math.max((vs.zoom || 0) - 1, 1) }));
  };

  return (
    <MapContainer>
      <DeckGL
        layers={allLayers}
        viewState={viewState}
        onViewStateChange={evt => setViewState(evt.viewState)}
        controller={true}
      >
        <Map
          mapLib={maplibregl}
          mapStyle={MAPLIBRE_STYLE}
        >
          {selectedLocation && (
            <Marker
              longitude={selectedLocation.longitude}
              latitude={selectedLocation.latitude}
              anchor="bottom"
              onClick={() => setShowPopup(true)}
            >
              <CustomMarker />
            </Marker>
          )}
          {selectedLocation && showPopup && (
            <Popup
              longitude={selectedLocation.longitude}
              latitude={selectedLocation.latitude}
              anchor="top"
              onClose={() => setShowPopup(false)}
              closeOnClick={false}
            >
              <PopupContent>
                <PopupAddress>{selectedLocation.address}</PopupAddress>
                <PopupPostcode>{selectedLocation.postcode}</PopupPostcode>
              </PopupContent>
            </Popup>
          )}
        </Map>
        <ZoomControls>
          <ZoomButton onClick={handleZoomIn} title="Zoom In">+</ZoomButton>
          <ZoomButton onClick={handleZoomOut} title="Zoom Out">-</ZoomButton>
        </ZoomControls>
      </DeckGL>
    </MapContainer>
  );
};

export default MapView; 