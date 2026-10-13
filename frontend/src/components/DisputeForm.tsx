import type { CategoryMeta, Trip } from '../api'

interface Props {
  trips: Trip[]
  categories: CategoryMeta[]
  selectedTripId: number | null
  category: string
  claimText: string
  filing: boolean
  onTripChange: (id: number) => void
  onCategoryChange: (c: string) => void
  onClaimTextChange: (t: string) => void
  onSubmit: () => void
}

export default function DisputeForm(props: Props) {
  const {
    trips,
    categories,
    selectedTripId,
    category,
    claimText,
    filing,
    onTripChange,
    onCategoryChange,
    onClaimTextChange,
    onSubmit,
  } = props

  return (
    <div className="card">
      <h2>File a dispute</h2>

      <label className="field">
        <span>Trip</span>
        <select
          value={selectedTripId ?? ''}
          onChange={(e) => onTripChange(Number(e.target.value))}
          disabled={trips.length === 0}
        >
          <option value="" disabled>
            {trips.length === 0 ? 'Loading trips…' : 'Select a trip'}
          </option>
          {trips.map((t) => (
            <option key={t.id} value={t.id}>
              #{t.id} · {t.rider} → {t.driver} · ${t.fare.toFixed(2)} · {t.scenario}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Category</span>
        <select value={category} onChange={(e) => onCategoryChange(e.target.value)}>
          {categories.map((c) => (
            <option key={c.value} value={c.value} disabled={!c.supported}>
              {c.label}
              {!c.supported ? ' (unsupported)' : ''}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Claim</span>
        <textarea rows={4} value={claimText} onChange={(e) => onClaimTextChange(e.target.value)} />
      </label>

      <button className="primary" disabled={selectedTripId === null || filing} onClick={onSubmit}>
        {filing ? 'Filing…' : 'File & Resolve'}
      </button>
    </div>
  )
}
