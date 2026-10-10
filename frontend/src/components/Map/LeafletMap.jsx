import React, { useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const DEFAULT_HUB = [12.9716, 77.5946];

export function isValidCoord(val) {
  return typeof val === 'number' && !isNaN(val) && isFinite(val);
}

export function isValidLatLng(arr) {
  return (
    Array.isArray(arr) &&
    arr.length === 2 &&
    isValidCoord(Number(arr[0])) &&
    isValidCoord(Number(arr[1]))
  );
}

function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click(e) {
      if (onMapClick && e.latlng && isValidCoord(e.latlng.lat) && isValidCoord(e.latlng.lng)) {
        onMapClick({
          latitude: Number(e.latlng.lat.toFixed(6)),
          longitude: Number(e.latlng.lng.toFixed(6)),
        });
      }
    },
  });
  return null;
}

function ChangeView({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (isValidLatLng(center)) {
      map.setView([Number(center[0]), Number(center[1])], zoom || map.getZoom());
    }
  }, [center, zoom, map]);
  return null;
}

export function LeafletMap({
  center = DEFAULT_HUB,
  zoom = 13,
  markers = [],
  polylines = [],
  geometry = null,
  routeColor = null,
  routeWeight = 4,
  routeOpacity = 0.8,
  onMapClick,
  children,
  className = '',
  style = { height: '100%', width: '100%' },
}) {
  const safeCenter = isValidLatLng(center)
    ? [Number(center[0]), Number(center[1])]
    : DEFAULT_HUB;

  const combinedPolylines = [...polylines];
  if (Array.isArray(geometry) && geometry.length >= 2) {
    combinedPolylines.push({
      positions: geometry,
      color: routeColor || '#2563eb',
      weight: routeWeight,
      opacity: routeOpacity,
    });
  }

  return (
    <div className={`relative w-full h-full min-h-[300px] overflow-hidden rounded-lg border border-gray-200 shadow-sm ${className}`}>
      <MapContainer
        center={safeCenter}
        zoom={zoom}
        style={style}
        scrollWheelZoom={true}
      >
        <ChangeView center={safeCenter} zoom={zoom} />

        {onMapClick && <MapClickHandler onMapClick={onMapClick} />}

        {/* Standard OpenStreetMap Tiles */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Route Polylines */}
        {combinedPolylines.map((polyline, idx) => {
          if (!Array.isArray(polyline.positions)) return null;
          const validPositions = polyline.positions
            .filter(isValidLatLng)
            .map((pos) => [Number(pos[0]), Number(pos[1])]);

          if (validPositions.length < 2) return null;


          return (
            <Polyline
              key={`polyline-${idx}`}
              positions={validPositions}
              pathOptions={{
                color: polyline.color || '#2563eb', // Default Blue
                weight: polyline.weight || 4,
                opacity: polyline.opacity || 0.8,
                dashArray: polyline.dashArray || null,
              }}
            />
          );
        })}

        {/* Simple Circle Markers per specification */}
        {markers.map((marker) => {
          const lat = Number(marker.lat ?? marker.latitude);
          const lng = Number(marker.lng ?? marker.longitude);
          if (!isValidCoord(lat) || !isValidCoord(lng)) return null;

          const color = marker.color || (
            marker.type === 'Hub' ? '#4b5563' : // Gray Hub
            marker.type === 'Agent' ? '#2563eb' : // Blue Agent
            marker.status === 'Delivered to hub' || marker.status === 'Delivered' ? '#16a34a' : // Green
            marker.status === 'Picked up' ? '#16a34a' :
            marker.status === 'En route' ? '#9333ea' : // Purple
            marker.status === 'Scheduled' ? '#2563eb' : // Blue
            marker.status === 'Unassigned' ? '#dc2626' : // Red
            '#d97706' // Amber / Pending
          );

          const radius = marker.radius || (marker.type === 'Hub' ? 9 : 7);

          return (
            <CircleMarker
              key={marker.id || `circle-${lat}-${lng}`}
              center={[lat, lng]}
              radius={radius}
              pathOptions={{
                color: color,
                fillColor: color,
                fillOpacity: 0.85,
                weight: 2,
              }}
            >
              {marker.popupContent && <Popup>{marker.popupContent}</Popup>}
            </CircleMarker>
          );
        })}

        {children}
      </MapContainer>
    </div>
  );
}

export default LeafletMap;
