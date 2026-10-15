import { useMemo } from 'react'
import type { TripGps } from '../api'

/**
 * Offline, tile-less route map rendered as inline SVG. Projects the
 * actual GPS trace and the optimal polyline to a normalised viewBox so
 * the picture fits its container at any width.
 *
 * Behaviour:
 *   - one shared projection (lat/lng to x/y) so both routes overlay
 *     correctly and don't drift apart visually
 *   - a 6% padding inside the viewBox so dots aren't clipped at the edges
 *   - pickup = first point of the optimal route, dropoff = last
 *   - if the actual trace and the optimal polyline are empty, renders
 *     an empty-state with a soft grid (still useful as a placeholder)
 *
 * Inputs are typed against `TripGps` so the backend schema is the
 * single source of truth.
 */
interface RouteSvgProps {
  gps: TripGps | null
  /** Extra padding (in viewBox units) around the route. Default 6. */
  pad?: number
  /** Optional className on the outer <svg>. */
  className?: string
}

interface ViewBox {
  minX: number
  minY: number
  width: number
  height: number
}

const VIEW_W = 1000
const VIEW_H = 480

function buildPolyline(
  pts: ReadonlyArray<[number, number]>,
  project: (lat: number, lng: number) => [number, number]
): { points: string; projected: Array<[number, number]> } {
  if (pts.length === 0) {
    return { points: '', projected: [] }
  }
  const projected = pts.map(([lat, lng]) => project(lat, lng))
  const points = projected.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(' ')
  return { points, projected }
}

function buildBounds(
  routes: Array<Array<[number, number]>>
): { minLat: number; maxLat: number; minLng: number; maxLng: number } {
  let minLat = Infinity
  let maxLat = -Infinity
  let minLng = Infinity
  let maxLng = -Infinity
  for (const route of routes) {
    for (const [lat, lng] of route) {
      if (lat < minLat) minLat = lat
      if (lat > maxLat) maxLat = lat
      if (lng < minLng) minLng = lng
      if (lng > maxLng) maxLng = lng
    }
  }
  if (!isFinite(minLat) || !isFinite(minLng)) {
    return { minLat: 0, maxLat: 1, minLng: 0, maxLng: 1 }
  }
  // Single point -> add a tiny delta so width/height don't collapse.
  if (minLat === maxLat) {
    minLat -= 0.0005
    maxLat += 0.0005
  }
  if (minLng === maxLng) {
    minLng -= 0.0005
    maxLng += 0.0005
  }
  return { minLat, maxLat, minLng, maxLng }
}

export default function RouteSvg({ gps, pad = 6, className }: RouteSvgProps) {
  const { viewBox, optimalPath, actualPath, pickupXY, dropoffXY, traceEmpty } = useMemo(() => {
    if (!gps) {
      return {
        viewBox: { minX: 0, minY: 0, width: VIEW_W, height: VIEW_H } as ViewBox,
        optimalPath: '',
        actualPath: '',
        pickupXY: null as [number, number] | null,
        dropoffXY: null as [number, number] | null,
        traceEmpty: true,
      }
    }

    const optimal: Array<[number, number]> = (gps.optimal_route ?? []) as Array<
      [number, number]
    >
    const actual: Array<[number, number]> = gps.points.map((p) => [p.lat, p.lng])

    const bounds = buildBounds([optimal, actual])
    const dataW = bounds.maxLng - bounds.minLng
    const dataH = bounds.maxLat - bounds.minLat

    // Maintain aspect ratio: compute scale so the data fits inside VIEW_W x VIEW_H
    // after padding, then centre it.
    const usableW = VIEW_W - pad * 2
    const usableH = VIEW_H - pad * 2
    const scale = Math.min(usableW / dataW, usableH / dataH)
    const offsetX = (VIEW_W - dataW * scale) / 2
    const offsetY = (VIEW_H - dataH * scale) / 2

    // The Y axis is inverted (lat grows north, SVG Y grows down). We also
    // flip X so east (larger lng) goes to the right.
    const project = (lat: number, lng: number): [number, number] => {
      const x = (lng - bounds.minLng) * scale + offsetX
      const y = (bounds.maxLat - lat) * scale + offsetY
      return [x, y]
    }

    const opt = buildPolyline(optimal, project)
    const act = buildPolyline(actual, project)

    const pickup = optimal.length > 0 ? project(optimal[0][0], optimal[0][1]) : null
    const dropoff =
      optimal.length > 0
        ? project(optimal[optimal.length - 1][0], optimal[optimal.length - 1][1])
        : null

    return {
      viewBox: { minX: 0, minY: 0, width: VIEW_W, height: VIEW_H } as ViewBox,
      optimalPath: opt.points,
      actualPath: act.points,
      pickupXY: pickup,
      dropoffXY: dropoff,
      traceEmpty: optimal.length === 0 && actual.length === 0,
    }
  }, [gps, pad])

  return (
    <div className={`rp-route-svg ${className ?? ''}`} aria-label="Route comparison">
      <svg
        viewBox={`${viewBox.minX} ${viewBox.minY} ${viewBox.width} ${viewBox.height}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label={
          traceEmpty
            ? 'Route map is empty because no GPS data is available.'
            : 'Map comparing the actual GPS trace and the optimal route.'
        }
      >
        {/* soft background grid for the empty state */}
        <defs>
          <pattern id="rp-route-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path
              d="M40 0H0V40"
              fill="none"
              stroke="rgba(20,22,38,0.05)"
              strokeWidth="1"
            />
          </pattern>
          <linearGradient id="rp-route-bg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#F4F7FB" />
            <stop offset="100%" stopColor="#E9EEF6" />
          </linearGradient>
        </defs>
        <rect x={0} y={0} width={VIEW_W} height={VIEW_H} fill="url(#rp-route-bg)" />
        <rect x={0} y={0} width={VIEW_W} height={VIEW_H} fill="url(#rp-route-grid)" />

        {traceEmpty && (
          <text
            x={VIEW_W / 2}
            y={VIEW_H / 2}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="20"
            fill="rgba(20,22,38,0.45)"
            fontWeight="600"
          >
            No GPS data for this trip
          </text>
        )}

        {/* optimal route: dashed blue, under the actual route */}
        {optimalPath && (
          <polyline
            points={optimalPath}
            fill="none"
            stroke="#1F64CC"
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray="10 8"
            opacity={0.85}
          />
        )}

        {/* actual route: solid red */}
        {actualPath && (
          <polyline
            points={actualPath}
            fill="none"
            stroke="#F0246E"
            strokeWidth={3.4}
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity={0.95}
          />
        )}

        {/* pickup marker (green) */}
        {pickupXY && (
          <g>
            <circle cx={pickupXY[0]} cy={pickupXY[1]} r={9} fill="#27AE60" />
            <circle
              cx={pickupXY[0]}
              cy={pickupXY[1]}
              r={9}
              fill="none"
              stroke="#fff"
              strokeWidth={3}
            />
            <text
              x={pickupXY[0]}
              y={pickupXY[1] - 16}
              textAnchor="middle"
              fontSize="12"
              fontWeight="700"
              fill="#1B1D24"
            >
              Pickup
            </text>
          </g>
        )}

        {/* dropoff marker (orange) */}
        {dropoffXY && (
          <g>
            <circle cx={dropoffXY[0]} cy={dropoffXY[1]} r={9} fill="#E67E22" />
            <circle
              cx={dropoffXY[0]}
              cy={dropoffXY[1]}
              r={9}
              fill="none"
              stroke="#fff"
              strokeWidth={3}
            />
            <text
              x={dropoffXY[0]}
              y={dropoffXY[1] - 16}
              textAnchor="middle"
              fontSize="12"
              fontWeight="700"
              fill="#1B1D24"
            >
              Dropoff
            </text>
          </g>
        )}
      </svg>
    </div>
  )
}
