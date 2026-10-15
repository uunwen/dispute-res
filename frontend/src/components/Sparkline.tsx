interface SparklineProps {
  /** Pre-computed Y values (0..1 normalized). At least 2 points recommended. */
  values: number[]
  color: string
  width?: number
  height?: number
  strokeWidth?: number
  ariaLabel?: string
}

/**
 * Tiny inline SVG sparkline. Renders a smooth line + soft area fill below.
 * No external dependencies. Hidden (returns null) if fewer than 2 points.
 */
export default function Sparkline({
  values,
  color,
  width = 96,
  height = 28,
  strokeWidth = 2,
  ariaLabel,
}: SparklineProps) {
  if (values.length < 2) return null
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const stepX = width / (values.length - 1)
  const points = values.map((v, i) => {
    const x = i * stepX
    const y = height - ((v - min) / range) * (height - 4) - 2
    return [x, y] as const
  })
  const linePath = points
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(' ')
  const areaPath = `${linePath} L${width.toFixed(1)},${height.toFixed(1)} L0,${height.toFixed(1)} Z`
  const gradId = `sl-grad-${color.replace('#', '')}`

  return (
    <svg
      className="rp-sparkline"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role={ariaLabel ? 'img' : 'presentation'}
      aria-label={ariaLabel}
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.28" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradId})`} />
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
