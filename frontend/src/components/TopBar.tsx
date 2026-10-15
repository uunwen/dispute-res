interface ValueProp {
  label: string
  blurb: string
  icon: string
}

const VALUES: ValueProp[] = [
  { label: 'Fair & Balanced', blurb: 'Both sides heard', icon: '⚖' },
  { label: 'Policy-Grounded', blurb: 'Transparent and consistent', icon: '📜' },
  { label: 'Fast Resolution', blurb: 'From days to minutes', icon: '⚡' },
  { label: 'Human Oversight', blurb: 'When it matters', icon: '👥' },
]

function Paw({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <circle cx="6" cy="10" r="2.2" />
      <circle cx="10" cy="6" r="2.2" />
      <circle cx="14" cy="6" r="2.2" />
      <circle cx="18" cy="10" r="2.2" />
      <path d="M12 11c-3.3 0-6 2.7-6 6 0 1.7 1.4 3 3 3h6c1.6 0 3-1.3 3-3 0-3.3-2.7-6-6-6z" />
    </svg>
  )
}

export default function TopBar() {
  return (
    <div className="rp-topbar">
      <div className="rp-topbar__brand">
        <div className="rp-topbar__mark">
          <div className="logo" aria-label="RumblePaws">
            <Paw size={20} />
          </div>
          <div className="name">
            <strong>RumblePaws</strong>
            <span>AI Dispute Resolution for Fairer Rides</span>
          </div>
        </div>
        <span className="rp-topbar__divider" />
        <div className="rp-topbar__tagline">
          <strong>Different Perspectives. One Fair Outcome.</strong>
          <span>Multi-agent AI to investigate, debate and resolve ride-hailing disputes.</span>
        </div>
      </div>
      <div className="rp-topbar__values" aria-label="Brand values">
        {VALUES.map((v) => (
          <div className="rp-topbar__value" key={v.label}>
            <span className="icon" aria-hidden>
              {v.icon}
            </span>
            <div className="text">
              <strong>{v.label}</strong>
              <span>{v.blurb}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
