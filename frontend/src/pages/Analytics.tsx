import type { DisputeListItem } from '../api'
import AnalyticsPane from './AnalyticsPane'

interface AnalyticsProps {
  disputes: DisputeListItem[]
  /** When set, the user can jump to /disputes filtered by the picked category. */
  onSelectCategory?: (category: string) => void
}

/**
 * Standalone /analytics page. Hosts the full-width version of
 * the analytics pane (with the time-window selector). The same
 * pane is embedded in the right rail of /disputes, so the two
 * screens are consistent.
 */
export default function Analytics({ disputes, onSelectCategory }: AnalyticsProps) {
  return (
    <div className="rp-page">
      <AnalyticsPane
        disputes={disputes}
        onSelectCategory={onSelectCategory}
        standalone
        showRangeSelector
      />
    </div>
  )
}
