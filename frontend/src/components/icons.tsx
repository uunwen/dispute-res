/* Small inline-SVG icon set used by the wizard and the dispute category grid.
 * Pure SVG, no external dependency, currentColor-friendly so callers can
 * recolor with CSS. */

interface IconProps {
  size?: number
  className?: string
  strokeWidth?: number
}

function base({ size = 22, className, strokeWidth = 1.8 }: IconProps) {
  return { size, className, strokeWidth }
}

export function RouteDeviationIcon(props: IconProps) {
  const { size, className, strokeWidth } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path
        d="M5 5c0 7 14 1 14 9 0 3-2 5-5 5"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />
      <circle cx="5" cy="5" r="1.6" fill="currentColor" />
      <circle cx="19" cy="19" r="1.6" fill="currentColor" />
    </svg>
  )
}

export function NoShowIcon(props: IconProps) {
  const { size, className, strokeWidth } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth={strokeWidth} />
      <path d="M6 6l12 12" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" />
    </svg>
  )
}

export function PropertyDamageIcon(props: IconProps) {
  const { size, className, strokeWidth } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path
        d="M14.7 6.3a4 4 0 1 0-5.4 5.4l-6 6a2.4 2.4 0 1 0 3.4 3.4l6-6a4 4 0 0 0 5.4-5.4l-2.5 2.5-1.4-1.4 2.5-2.5z"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function SafetyIncidentIcon(props: IconProps) {
  const { size, className, strokeWidth } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path
        d="M12 3l9 4v6c0 4.5-3.4 8.4-9 9-5.6-.6-9-4.5-9-9V7l9-4z"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
      />
      <path
        d="M12 9v4"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />
      <circle cx="12" cy="16" r="1" fill="currentColor" />
    </svg>
  )
}

export function UploadIcon(props: IconProps) {
  const { size = 28, className, strokeWidth = 1.6 } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path
        d="M12 16V5m0 0l-4 4m4-4l4 4"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />
    </svg>
  )
}

export function PhotoIcon(props: IconProps) {
  const { size = 22, className, strokeWidth = 1.6 } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" strokeWidth={strokeWidth} />
      <circle cx="9" cy="11" r="1.6" fill="currentColor" />
      <path
        d="M21 17l-5-5-7 7"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function ChatIcon(props: IconProps) {
  const { size = 22, className, strokeWidth = 1.6 } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path
        d="M4 5h16v11H8l-4 4V5z"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function ReceiptIcon(props: IconProps) {
  const { size = 22, className, strokeWidth = 1.6 } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path
        d="M6 3h12v18l-3-2-3 2-3-2-3 2V3z"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
      />
      <path
        d="M9 8h6M9 12h6M9 16h4"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />
    </svg>
  )
}

export function FileIcon(props: IconProps) {
  const { size = 22, className, strokeWidth = 1.6 } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path
        d="M7 3h8l4 4v14H7V3z"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
      />
      <path d="M14 3v5h5" stroke="currentColor" strokeWidth={strokeWidth} strokeLinejoin="round" />
    </svg>
  )
}

export function PlusIcon(props: IconProps) {
  const { size = 22, className, strokeWidth = 2 } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" />
    </svg>
  )
}

export function CloseIcon(props: IconProps) {
  const { size = 16, className, strokeWidth = 2 } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path
        d="M6 6l12 12M18 6L6 18"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />
    </svg>
  )
}

export function PencilIcon(props: IconProps) {
  const { size = 16, className, strokeWidth = 1.6 } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path
        d="M4 20h4l10-10-4-4L4 16v4z"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
      />
      <path d="M14 6l4 4" stroke="currentColor" strokeWidth={strokeWidth} />
    </svg>
  )
}

export function CheckIcon(props: IconProps) {
  const { size = 14, className, strokeWidth = 2.4 } = base(props)
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path
        d="M5 12.5l4.5 4.5L19 7"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
