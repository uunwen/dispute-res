import { CircleMarker, MapContainer, Polyline, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { TripGps } from '../api'

interface Props {
  gps: TripGps | null
}

export default function RouteMap({ gps }: Props) {
  if (!gps || gps.points.length === 0) return null

  const route: [number, number][] = gps.optimal_route ?? []
  const trace: [number, number][] = gps.points.map((p) => [p.lat, p.lng])
  const pickup = route[0]
  const dropoff = route[route.length - 1]
  const center: [number, number] = pickup ?? trace[0] ?? [1.35, 103.82]

  return (
    <div className="card">
      <h2>Route map</h2>
      <div className="map-wrap">
        <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {route.length > 1 && (
            <Polyline positions={route} pathOptions={{ color: '#2f80ed', weight: 3, dashArray: '6 6' }} />
          )}
          {trace.length > 1 && (
            <Polyline positions={trace} pathOptions={{ color: '#eb5757', weight: 3 }} />
          )}
          {pickup && (
            <CircleMarker center={pickup} radius={6} pathOptions={{ color: '#27ae60', fillColor: '#27ae60', fillOpacity: 1 }} />
          )}
          {dropoff && (
            <CircleMarker center={dropoff} radius={6} pathOptions={{ color: '#e67e22', fillColor: '#e67e22', fillOpacity: 1 }} />
          )}
        </MapContainer>
      </div>
      <div className="legend small muted">
        <span>
          <i className="legend-dot" style={{ background: '#eb5757' }} /> actual GPS
        </span>
        <span>
          <i className="legend-dot" style={{ background: '#2f80ed' }} /> optimal route
        </span>
        <span>
          <i className="legend-dot" style={{ background: '#27ae60' }} /> pickup
        </span>
        <span>
          <i className="legend-dot" style={{ background: '#e67e22' }} /> dropoff
        </span>
      </div>
    </div>
  )
}
