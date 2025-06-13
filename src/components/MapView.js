import React, { useState, useEffect } from 'react';
import Map, { Marker, Popup } from 'react-map-gl';
import { DeckGL, GeoJsonLayer } from 'deck.gl';
import styled, { createGlobalStyle } from 'styled-components';
import maplibregl from 'maplibre-gl';
import RoomIcon from '@mui/icons-material/Room';
import ErrorIcon from '@mui/icons-material/Error';
import CategoryIcon from '@mui/icons-material/Category';
import DescriptionIcon from '@mui/icons-material/Description';
import TimerIcon from '@mui/icons-material/Timer';
import RepeatIcon from '@mui/icons-material/Repeat';
import WarningIcon from '@mui/icons-material/Warning';
import { keyframes } from 'styled-components';

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

const fadeIn = keyframes`
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const PopupContent = styled.div`
  padding: 15px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  animation: ${fadeIn} 0.3s ease-out;
`;

const PopupTitle = styled.div`
  font-size: 1.2em;
  font-weight: bold;
  color: #01a3a4;
  margin-bottom: 16px;
  border-bottom: 2px solid #01a3a4;
  padding-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const PropertyGroup = styled.div`
  margin-bottom: 16px;
  padding: 12px;
  background: ${props => {
    if (props.type === 'crm') {
      switch (props.status?.toLowerCase()) {
        case 'open':
          return '#fff5f5';
        case 'in progress':
          return '#fff9f0';
        case 'closed':
          return '#f7fcf7';
        default:
          return '#f8f9fa';
      }
    }
    return props.severity === 'high' ? '#fff5f5' : 
           props.severity === 'medium' ? '#fff9f0' : 
           '#f7fcf7';
  }};
  border-radius: 6px;
  border-left: 4px solid ${props => {
    if (props.type === 'crm') {
      switch (props.status?.toLowerCase()) {
        case 'open':
          return '#d32f2f';
        case 'in progress':
          return '#f57c00';
        case 'closed':
          return '#4caf50';
        default:
          return '#90a4ae';
      }
    }
    return props.severity === 'high' ? '#ff4d4d' : 
           props.severity === 'medium' ? '#ffa726' : 
           '#4caf50';
  }};
`;

const PropertyRow = styled.div`
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
  gap: 8px;
  
  &:last-child {
    margin-bottom: 0;
  }
`;

const PropertyLabel = styled.div`
  font-weight: 600;
  color: #546e7a;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 120px;
  
  svg {
    font-size: 1.2em;
    color: #01a3a4;
  }
`;

const PropertyValue = styled.div`
  color: #37474f;
  flex: 1;
  line-height: 1.4;
`;

const LoadingSpinner = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: #01a3a4;
  
  &:after {
    content: '';
    width: 20px;
    height: 20px;
    border: 2px solid #01a3a4;
    border-top: 2px solid transparent;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const ErrorMessage = styled.div`
  color: #d32f2f;
  padding: 12px;
  background: #ffebee;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  
  svg {
    font-size: 1.2em;
  }
`;

const GlobalStyle = createGlobalStyle`
  .defect-popup {
    .maplibregl-popup-content {
      padding: 0;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    
    .maplibregl-popup-close-button {
      padding: 0;
      width: 24px;
      height: 24px;
      color: white;
      font-size: 24px;
      background: rgba(0,0,0,0.2);
      border-radius: 50%;
      right: 8px;
      top: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1;
      
      &:hover {
        background: rgba(0,0,0,0.4);
      }
    }
    
    .maplibregl-popup-tip {
      border-top-color: white;
    }
  }
`;

const MapView = ({ viewState, setViewState, selectedLocation, displayedLocations = [] }) => {
  const [showPopup, setShowPopup] = useState(false);
  const [popupLocation, setPopupLocation] = useState(null);
  const [locationInfo, setLocationInfo] = useState(null);
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [errorInfo, setErrorInfo] = useState(null);

  // Add new useEffect for auto-zooming to show all markers
  useEffect(() => {
    if (displayedLocations.length > 0) {
      // Calculate bounds
      const lats = displayedLocations.map(loc => loc.latitude);
      const lons = displayedLocations.map(loc => loc.longitude);
      
      const minLat = Math.min(...lats);
      const maxLat = Math.max(...lats);
      const minLon = Math.min(...lons);
      const maxLon = Math.max(...lons);
      
      // Add padding to bounds
      const latPadding = (maxLat - minLat) * 0.2;
      const lonPadding = (maxLon - minLon) * 0.2;
      
      // Calculate center
      const centerLat = (minLat + maxLat) / 2;
      const centerLon = (minLon + maxLon) / 2;
      
      // Calculate zoom level
      const latZoom = Math.log2(360 / (maxLat - minLat + 2 * latPadding)) + 1;
      const lonZoom = Math.log2(360 / (maxLon - minLon + 2 * lonPadding)) + 1;
      const zoom = Math.min(latZoom, lonZoom, 20);
      
      setViewState({
        latitude: centerLat,
        longitude: centerLon,
        zoom: zoom - 1, // Subtract 1 to zoom out slightly more
        bearing: 0,
        pitch: 0,
        padding: { top: 50, bottom: 50, left: 50, right: 50 }
      });
    }
  }, [displayedLocations, setViewState]);

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
      const res = await fetch(`http://localhost:8000/api/defect-by-location?latitude=${loc.latitude}&longitude=${loc.longitude}`);
      const data = await res.json();
      if (data.defect) {
        setLocationInfo(data.defect);
      } else {
        setErrorInfo('No defect found at this location.');
      }
    } catch (error) {
      setErrorInfo('Failed to fetch defect information.');
    } finally {
      setLoadingInfo(false);
    }
  };

  return (
    <MapContainer>
      <GlobalStyle />
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
            onClick={() => handleMarkerClick(loc)}
          >
            <RoomIcon style={{ fontSize: 36, color: '#d32f2f', filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.3))', cursor: 'pointer', pointerEvents: 'auto' }} />
          </Marker>
        ))}
        {showPopup && popupLocation && (
          <Popup
            longitude={popupLocation.longitude}
            latitude={popupLocation.latitude}
            anchor="top"
            onClose={() => setShowPopup(false)}
            closeOnClick={false}
            className="defect-popup"
          >
            <PopupContent>
              <PopupTitle>
                <WarningIcon />
                Defect Information
              </PopupTitle>
              
              {loadingInfo && <LoadingSpinner />}
              
              {errorInfo && (
                <ErrorMessage>
                  <ErrorIcon />
                  {errorInfo}
                </ErrorMessage>
              )}
              
              {locationInfo && (
                <>
                  <PropertyGroup severity={locationInfo.severity?.toLowerCase()}>
                    <PropertyRow>
                      <PropertyLabel>
                        <CategoryIcon />
                        ID
                      </PropertyLabel>
                      <PropertyValue>{locationInfo.defect_id}</PropertyValue>
                    </PropertyRow>
                    
                    <PropertyRow>
                      <PropertyLabel>
                        <CategoryIcon />
                        Category
                      </PropertyLabel>
                      <PropertyValue>{locationInfo.category}</PropertyValue>
                    </PropertyRow>
                    
                    <PropertyRow>
                      <PropertyLabel>
                        <WarningIcon />
                        Severity
                      </PropertyLabel>
                      <PropertyValue style={{
                        color: locationInfo.severity?.toLowerCase() === 'high' ? '#d32f2f' :
                               locationInfo.severity?.toLowerCase() === 'medium' ? '#f57c00' :
                               '#388e3c',
                        fontWeight: 'bold'
                      }}>
                        {locationInfo.severity}
                      </PropertyValue>
                    </PropertyRow>

                    <PropertyRow>
                      <PropertyLabel>
                        <DescriptionIcon />
                        Description
                      </PropertyLabel>
                      <PropertyValue>{locationInfo.description}</PropertyValue>
                    </PropertyRow>

                    <PropertyRow>
                      <PropertyLabel>
                        <RepeatIcon />
                        Times Detected
                      </PropertyLabel>
                      <PropertyValue>{locationInfo.timesDetected}</PropertyValue>
                    </PropertyRow>
                  </PropertyGroup>

                  {locationInfo.crm_case && (
                    <PropertyGroup type="crm" status={locationInfo.crm_case.status}>
                      <PropertyRow>
                        <PropertyLabel>
                          <DescriptionIcon />
                          Case ID
                        </PropertyLabel>
                        <PropertyValue>{locationInfo.crm_case.case_id}</PropertyValue>
                      </PropertyRow>

                      <PropertyRow>
                        <PropertyLabel>
                          <CategoryIcon />
                          Status
                        </PropertyLabel>
                        <PropertyValue style={{
                          color: locationInfo.crm_case.status?.toLowerCase() === 'open' ? '#d32f2f' :
                                 locationInfo.crm_case.status?.toLowerCase() === 'in progress' ? '#f57c00' :
                                 '#388e3c',
                          fontWeight: 'bold'
                        }}>
                          {locationInfo.crm_case.status}
                        </PropertyValue>
                      </PropertyRow>

                      <PropertyRow>
                        <PropertyLabel>
                          <DescriptionIcon />
                          Description
                        </PropertyLabel>
                        <PropertyValue>{locationInfo.crm_case.description}</PropertyValue>
                      </PropertyRow>

                      <PropertyRow>
                        <PropertyLabel>
                          <TimerIcon />
                          Created At
                        </PropertyLabel>
                        <PropertyValue>
                          {new Date(locationInfo.crm_case.createdAt).toLocaleString()}
                        </PropertyValue>
                      </PropertyRow>
                    </PropertyGroup>
                  )}
                </>
              )}
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
