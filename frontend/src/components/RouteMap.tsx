import { useEffect, useMemo } from 'react'
import { CircleMarker, MapContainer, Polyline, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { TripGps } from '../api'

interface Props {
  gps: TripGps | null
  className?: string
  height?: number | string
}

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length === 0) return
    const lats = points.map((p) => p[0])
    const lngs = points.map((p) => p[1])
    const minLat = Math.min(...lats)
    const maxLat = Math.max(...lats)
    const minLng = Math.min(...lngs)
    const maxLng = Math.max(...lngs)
    if (minLat === maxLat && minLng === maxLng) {
      map.setView([minLat, minLng], 16)
      return
    }
    map.fitBounds(
      [
        [minLat, minLng],
        [maxLat, maxLng],
      ],
      { padding: [40, 40] },
    )
  }, [map, points])
  return null
}

export default function RouteMap({ gps, className, height = 360 }: Props) {
  const route: [number, number][] = useMemo(
    () => (gps?.optimal_route ?? []) as [number, number][],
    [gps],
  )
  const trace: [number, number][] = useMemo(
    () => (gps ? gps.points.map((p) => [p.lat, p.lng] as [number, number]) : []),
    [gps],
  )

  if (!gps || trace.length === 0) return null

  const pickup = route[0] ?? trace[0]
  const dropoff = route[route.length - 1] ?? trace[trace.length - 1]
  const center: [number, number] = pickup ?? [1.35, 103.82]
  const bounds = [...route, ...trace]

  return (
    <div
      className={`rp-route-map ${className ?? ''}`}
      style={{ height }}
    >
      <MapContainer center={center} zoom={14} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={bounds} />
        {route.length > 1 && (
          <Polyline
            positions={route}
            pathOptions={{ color: '#1F64CC', weight: 3, dashArray: '6 6' }}
          />
        )}
        {trace.length > 1 && (
          <Polyline
            positions={trace}
            pathOptions={{ color: '#F0246E', weight: 3 }}
          />
        )}
        {pickup && (
          <CircleMarker
            center={pickup}
            radius={7}
            pathOptions={{ color: '#27ae60', fillColor: '#27ae60', fillOpacity: 1 }}
          />
        )}
        {dropoff && (
          <CircleMarker
            center={dropoff}
            radius={7}
            pathOptions={{ color: '#e67e22', fillColor: '#e67e22', fillOpacity: 1 }}
          />
        )}
      </MapContainer>
    </div>
  )
}
