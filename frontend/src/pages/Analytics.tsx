import { useEffect, useMemo, useState } from 'react'
import { api, type DisputeListItem } from '../api'
import AnalyticsPane from './AnalyticsPane'

interface AnalyticsProps {
  /** The persona's account id (null for ops). */
  accountId: number | null
  /** When set, the user can jump to /disputes filtered by the picked category. */
  onSelectCategory?: (category: string) => void
}

/**
 * Standalone /analytics page. Hosts the full-width version of the analytics
 * pane. Unlike the other screens (which use the persona-driven shared list),
 * analytics fetches its own data so it can include synthetic variants by
 * default via its own toggle.
 */
export default function Analytics({ accountId, onSelectCategory }: AnalyticsProps) {
  const [includeSynthetic, setIncludeSynthetic] = useState(true)
  const [disputes, setDisputes] = useState<DisputeListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .listDisputes({ account_id: accountId, include_synthetic: includeSynthetic })
      .then((items) => {
        if (cancelled) return
        setDisputes(items)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load disputes.')
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [accountId, includeSynthetic])

  function handleIncludeSyntheticChange(next: boolean) {
    setLoading(true)
    setIncludeSynthetic(next)
  }

  const syntheticCount = useMemo(
    () =>
      disputes.filter(
        (d) => typeof d.external_id === 'string' && d.external_id.startsWith('VAR-'),
      ).length,
    [disputes],
  )

  return (
    <div className="rp-page">
      <AnalyticsPane
        disputes={disputes}
        loading={loading}
        error={error}
        onSelectCategory={onSelectCategory}
        standalone
        showRangeSelector
        includeSynthetic={includeSynthetic}
        syntheticCount={syntheticCount}
        onIncludeSyntheticChange={handleIncludeSyntheticChange}
      />
    </div>
  )
}
