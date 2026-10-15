import { type ReactNode } from 'react'

interface SidebarItem {
  key: string
  label: string
  icon: ReactNode
}

interface SidebarProps {
  activeKey: string
  onSelect: (key: string) => void
  items: SidebarItem[]
  profile?: { name: string; role: string }
}

const Paw = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
    <circle cx="6" cy="10" r="2.2" />
    <circle cx="10" cy="6" r="2.2" />
    <circle cx="14" cy="6" r="2.2" />
    <circle cx="18" cy="10" r="2.2" />
    <path d="M12 11c-3.3 0-6 2.7-6 6 0 1.7 1.4 3 3 3h6c1.6 0 3-1.3 3-3 0-3.3-2.7-6-6-6z" />
  </svg>
)

export default function Sidebar({ activeKey, onSelect, items, profile }: SidebarProps) {
  return (
    <aside className="rp-sidebar">
      <div className="rp-sidebar__brand">
        <span className="rp-sidebar__paw" style={{ color: '#fff' }}>
          <Paw />
        </span>
        <div className="rp-sidebar__title">
          <strong>RumblePaws</strong>
          <span>Dispute Resolution</span>
        </div>
      </div>

      <div className="rp-sidebar__section">Main</div>
      <nav className="rp-sidebar__nav">
        {items.map((item) => (
          <button
            key={item.key}
            className={`rp-sidebar__item ${item.key === activeKey ? 'active' : ''}`}
            onClick={() => onSelect(item.key)}
            type="button"
          >
            <span className="icon">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {profile && (
        <div className="rp-sidebar__profile">
          <span className="avatar" aria-hidden>
            {profile.name
              .split(' ')
              .map((n) => n[0])
              .slice(0, 2)
              .join('')}
          </span>
          <div className="meta">
            <strong>{profile.name}</strong>
            <span>{profile.role}</span>
          </div>
        </div>
      )}
    </aside>
  )
}
