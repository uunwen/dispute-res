import { type ReactElement, useEffect, useMemo, useRef, useState } from 'react'
import { api, type CategoryMeta, type Trip } from '../api'
import StepProgress from '../components/StepProgress'
import {
  ChatIcon,
  CheckIcon,
  CloseIcon,
  FileIcon,
  PencilIcon,
  PhotoIcon,
  PlusIcon,
  PropertyDamageIcon,
  ReceiptIcon,
  RouteDeviationIcon,
  SafetyIncidentIcon,
  UploadIcon,
  NoShowIcon,
} from '../components/icons'
import { categoryLabel } from '../lib/status'

type StepKey = 'details' | 'evidence' | 'review' | 'submit'

const STEPS: { key: StepKey; label: string }[] = [
  { key: 'details', label: 'Details' },
  { key: 'evidence', label: 'Evidence' },
  { key: 'review', label: 'Review' },
  { key: 'submit', label: 'Submit' },
]

/* Categories shown in the wizard (matches the design's 2x2 grid).
 * The backend also exposes `fare_dispute`; we keep it in the API list for
 * the global category meta but filter to the four design cards here. */
const WIZARD_CATEGORIES: { value: string; label: string; blurb: string }[] = [
  {
    value: 'route_deviation',
    label: 'Route deviation',
    blurb: 'Driver took a longer or inappropriate route',
  },
  {
    value: 'no_show',
    label: 'No-show',
    blurb: 'Driver charged cancellation or waiting fee',
  },
  {
    value: 'property_damage',
    label: 'Property damage',
    blurb: 'Cleaning fee or vehicle damage',
  },
  {
    value: 'safety_incident',
    label: 'Safety incident',
    blurb: 'Misconduct or safety concern',
  },
]

const CATEGORY_ICONS: Record<string, (p: { size?: number }) => ReactElement> = {
  route_deviation: (p) => <RouteDeviationIcon size={p.size} />,
  no_show: (p) => <NoShowIcon size={p.size} />,
  property_damage: (p) => <PropertyDamageIcon size={p.size} />,
  safety_incident: (p) => <SafetyIncidentIcon size={p.size} />,
}

const CLAIM_MAX = 500
const FILE_MAX_BYTES = 10 * 1024 * 1024
const FILE_TYPES: Record<string, string[]> = {
  photos_videos: ['image/jpeg', 'image/png', 'image/webp', 'video/mp4'],
  chat_logs: ['image/jpeg', 'image/png', 'image/webp', 'text/plain', 'application/json'],
  receipts: ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'],
  other_files: [], // accept anything not caught by the others
}

type ChipKey = keyof typeof FILE_TYPES

const CHIPS: { key: ChipKey; label: string; icon: (p: { size?: number }) => ReactElement }[] = [
  { key: 'photos_videos', label: 'Photos/Videos', icon: (p) => <PhotoIcon size={p.size} /> },
  { key: 'chat_logs', label: 'Chat Logs', icon: (p) => <ChatIcon size={p.size} /> },
  { key: 'receipts', label: 'Receipts', icon: (p) => <ReceiptIcon size={p.size} /> },
  { key: 'other_files', label: 'Other Files', icon: (p) => <FileIcon size={p.size} /> },
]

interface FileEntry {
  id: string
  name: string
  size: number
  type: string
  /** A small data: URL for in-browser preview (images only). */
  previewUrl: string | null
  chip: ChipKey
  error?: string
}

interface FileDisputeProps {
  onCancel: () => void
  /** Called once the backend returns the created Dispute. */
  onSubmitted: (disputeId: number) => void
}

export default function FileDispute({ onCancel, onSubmitted }: FileDisputeProps) {
  /* ---------- state (kept across all steps) ---------- */
  const [step, setStep] = useState<StepKey>('details')
  const [trips, setTrips] = useState<Trip[]>([])
  const [categories, setCategories] = useState<CategoryMeta[]>([])
  const [loadingTrips, setLoadingTrips] = useState(true)
  const [tripsError, setTripsError] = useState<string | null>(null)
  const [drawerTripId, setDrawerTripId] = useState<number | null>(null)

  const [tripId, setTripId] = useState<number | null>(null)
  const [category, setCategory] = useState<string | null>(null)
  const [claim, setClaim] = useState('')

  const [files, setFiles] = useState<FileEntry[]>([])
  const [activeChip, setActiveChip] = useState<ChipKey>('photos_videos')
  const [confirmed, setConfirmed] = useState(false)

  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  /* ---------- load trip + category lists once ---------- */
  useEffect(() => {
    let cancelled = false
    Promise.all([api.listTrips(), api.fetchCategories()])
      .then(([t, c]) => {
        if (cancelled) return
        setTrips(t)
        setCategories(c)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setTripsError(err instanceof Error ? err.message : 'Failed to load trips.')
      })
      .finally(() => {
        if (cancelled) return
        setLoadingTrips(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  /* ---------- derived ---------- */
  const selectedTrip = useMemo(
    () => (tripId ? trips.find((t) => t.id === tripId) ?? null : null),
    [tripId, trips],
  )
  const selectedCategory = useMemo(
    () =>
      category
        ? categories.find((c) => c.value === category) ?? {
            value: category,
            label: categoryLabel(category),
            example_claim: '',
            supported: true,
          }
        : null,
    [category, categories],
  )

  const canGoNextFromDetails = tripId !== null && category !== null && claim.trim().length > 0
  const canGoNextFromEvidence = confirmed
  const evidenceCount = files.length

  /* ---------- handlers ---------- */
  function gotoStep(next: StepKey) {
    setStep(next)
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  function addFiles(list: FileList | File[]) {
    const accepted = Array.from(list)
    if (accepted.length === 0) return
    const allowList = FILE_TYPES[activeChip]
    const acceptAnything = allowList.length === 0
    const next: FileEntry[] = []
    for (const f of accepted) {
      const isImage = f.type.startsWith('image/')
      const previewUrl = isImage ? URL.createObjectURL(f) : null
      const entry: FileEntry = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        name: f.name,
        size: f.size,
        type: f.type || 'application/octet-stream',
        previewUrl,
        chip: activeChip,
      }
      if (f.size > FILE_MAX_BYTES) {
        entry.error = `File is larger than 10MB.`
      } else if (!acceptAnything && !allowList.includes(f.type)) {
        entry.error = `Type not allowed for this section.`
      }
      next.push(entry)
    }
    setFiles((prev) => [...prev, ...next])
  }

  function removeFile(id: string) {
    setFiles((prev) => {
      const target = prev.find((f) => f.id === id)
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl)
      return prev.filter((f) => f.id !== id)
    })
  }

  function chipCount(key: ChipKey): number {
    return files.filter((f) => f.chip === key && !f.error).length
  }

  async function submit() {
    if (tripId === null || category === null) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      // MOCK: no backend file-upload endpoint. We send only the structured
      // case JSON the backend expects: { trip_id, category, claim_text,
      // filed_by }. The file list is shown to the user (Review step) but
      // is not sent; the dispute card surfaces the
      // "Evidence images are listed, not analysed, in this version." note
      // so users don't expect the LLM to have looked at the files.
      const created = await api.createDispute({
        trip_id: tripId,
        category,
        claim_text: claim.trim(),
        filed_by: 1, // MOCK: hard-coded claimant; auth not wired in this MVP
      })
      onSubmitted(created.id)
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to submit dispute.')
    } finally {
      setSubmitting(false)
    }
  }

  /* ---------- render ---------- */
  return (
    <div className="rp-page rp-file-dispute">
      <div className="rp-page-header">
        <div>
          <h1>File a Dispute</h1>
          <p>Guided submission flow</p>
        </div>
      </div>

      <div className="rp-wizard">
        <StepProgress steps={STEPS} currentKey={step} />

        {step === 'details' && (
          <DetailsStep
            trips={trips}
            loadingTrips={loadingTrips}
            tripsError={tripsError}
            tripId={tripId}
            onTripChange={setTripId}
            onViewTrip={setDrawerTripId}
            category={category}
            onCategoryChange={setCategory}
            claim={claim}
            onClaimChange={setClaim}
            onCancel={onCancel}
            onNext={() => gotoStep('evidence')}
            canNext={canGoNextFromDetails}
          />
        )}

        {step === 'evidence' && (
          <EvidenceStep
            activeChip={activeChip}
            onActiveChipChange={setActiveChip}
            files={files}
            onAddFiles={addFiles}
            onRemoveFile={removeFile}
            chipCount={chipCount}
            confirmed={confirmed}
            onConfirmChange={setConfirmed}
            onBack={() => gotoStep('details')}
            onNext={() => gotoStep('review')}
            canNext={canGoNextFromEvidence}
          />
        )}

        {step === 'review' && (
          <ReviewStep
            trip={selectedTrip}
            categoryLabel={selectedCategory ? categoryLabel(selectedCategory.value) : ''}
            claim={claim}
            evidenceCount={evidenceCount}
            files={files}
            onEdit={() => gotoStep('details')}
            onBack={() => gotoStep('evidence')}
            onSubmit={submit}
            submitting={submitting}
            submitError={submitError}
            onCancel={onCancel}
          />
        )}

        {step === 'submit' && selectedTrip && selectedCategory && (
          <SubmittingStep
            trip={selectedTrip}
            categoryLabel={categoryLabel(selectedCategory.value)}
            claim={claim}
            fileCount={evidenceCount}
            submitting={submitting}
            error={submitError}
            onRetry={submit}
          />
        )}
      </div>

      <TripDrawer
        trip={drawerTripId ? trips.find((t) => t.id === drawerTripId) ?? null : null}
        onClose={() => setDrawerTripId(null)}
      />
    </div>
  )
}

/* ====================================================================
 * Step 1 — Details
 * ==================================================================== */
interface DetailsStepProps {
  trips: Trip[]
  loadingTrips: boolean
  tripsError: string | null
  tripId: number | null
  onTripChange: (id: number) => void
  onViewTrip: (id: number) => void
  category: string | null
  onCategoryChange: (c: string) => void
  claim: string
  onClaimChange: (s: string) => void
  onCancel: () => void
  onNext: () => void
  canNext: boolean
}

function DetailsStep({
  trips,
  loadingTrips,
  tripsError,
  tripId,
  onTripChange,
  onViewTrip,
  category,
  onCategoryChange,
  claim,
  onClaimChange,
  onCancel,
  onNext,
  canNext,
}: DetailsStepProps) {
  return (
    <div className="rp-wizard__step">
      <h2>Select Trip</h2>
      <p className="subtitle">Pick the trip you want to dispute.</p>

      <div className="rp-field rp-field--row">
        <select
          className="rp-select"
          aria-label="Trip"
          disabled={loadingTrips || !!tripsError}
          value={tripId ?? ''}
          onChange={(e) => onTripChange(Number(e.target.value))}
        >
          <option value="" disabled>
            {loadingTrips
              ? 'Loading trips…'
              : tripsError
                ? tripsError
                : trips.length === 0
                  ? 'No trips available'
                  : 'Select a trip'}
          </option>
          {trips.map((t) => (
            <option key={t.id} value={t.id}>
              {tripOptionLabel(t)}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="rp-link"
          onClick={() => tripId !== null && onViewTrip(tripId)}
          disabled={tripId === null}
        >
          View trip details
        </button>
      </div>

      <h2 className="rp-wizard__h2">Select Dispute Category</h2>
      <p className="subtitle">Choose what best describes the issue.</p>
      <div className="rp-category-grid">
        {WIZARD_CATEGORIES.map((c) => {
          const selected = c.value === category
          const Icon = CATEGORY_ICONS[c.value] ?? RouteDeviationIcon
          return (
            <button
              key={c.value}
              type="button"
              className={`rp-category-card ${selected ? 'selected' : ''}`}
              onClick={() => onCategoryChange(c.value)}
            >
              <span className="rp-category-card__icon" aria-hidden>
                <Icon size={22} />
              </span>
              <span className="label">{c.label}</span>
              <span className="blurb">{c.blurb}</span>
              {selected && (
                <span className="rp-category-card__check" aria-hidden>
                  <CheckIcon size={12} />
                </span>
              )}
            </button>
          )
        })}
      </div>

      <h2 className="rp-wizard__h2">Describe your claim</h2>
      <p className="subtitle">Tell us what happened. Be as specific as you can.</p>
      <div className="rp-field">
        <textarea
          value={claim}
          onChange={(e) => onClaimChange(e.target.value.slice(0, CLAIM_MAX))}
          maxLength={CLAIM_MAX}
          rows={4}
          placeholder="Describe the issue in your own words…"
        />
        <div className="rp-counter">
          <span className={claim.length >= CLAIM_MAX ? 'is-max' : ''}>
            {claim.length}/{CLAIM_MAX}
          </span>
        </div>
      </div>

      <div className="rp-wizard__footer">
        <button type="button" className="rp-btn rp-btn--ghost" onClick={onCancel}>
          Cancel
        </button>
        <button
          type="button"
          className="rp-btn rp-btn--primary"
          onClick={onNext}
          disabled={!canNext}
          title={canNext ? undefined : 'Pick a trip, a category and write a claim first.'}
        >
          Next: Upload Evidence →
        </button>
      </div>
    </div>
  )
}

function tripOptionLabel(t: Trip): string {
  // MOCK: the backend's TripListItem does not include requested_at, so
  // we render only what the API actually gives us.
  return `Trip #${t.id}  ·  ${t.rider} → ${t.driver}  ·  $${t.fare.toFixed(2)}`
}

/* ====================================================================
 * Step 2 — Evidence
 * ==================================================================== */
interface EvidenceStepProps {
  activeChip: ChipKey
  onActiveChipChange: (k: ChipKey) => void
  files: FileEntry[]
  onAddFiles: (list: FileList | File[]) => void
  onRemoveFile: (id: string) => void
  chipCount: (k: ChipKey) => number
  confirmed: boolean
  onConfirmChange: (b: boolean) => void
  onBack: () => void
  onNext: () => void
  canNext: boolean
}

function EvidenceStep({
  activeChip,
  onActiveChipChange,
  files,
  onAddFiles,
  onRemoveFile,
  chipCount,
  confirmed,
  onConfirmChange,
  onBack,
  onNext,
  canNext,
}: EvidenceStepProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [topError, setTopError] = useState<string | null>(null)

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files?.length) {
      onAddFiles(e.dataTransfer.files)
    }
  }

  return (
    <div className="rp-wizard__step">
      <h2>Add Evidence <span className="rp-optional">(optional)</span></h2>
      <p className="subtitle">Drop in photos, chat screenshots or receipts.</p>

      <div className="rp-evidence__chips" role="tablist">
        {CHIPS.map((chip) => {
          const Icon = chip.icon
          const selected = chip.key === activeChip
          return (
            <button
              type="button"
              key={chip.key}
              role="tab"
              aria-selected={selected}
              className={`rp-evidence__chip ${selected ? 'is-selected' : ''}`}
              onClick={() => {
                onActiveChipChange(chip.key)
                setTopError(null)
              }}
            >
              <Icon size={16} />
              <span>{chip.label}</span>
              {chipCount(chip.key) > 0 && (
                <span className="rp-evidence__chip-count">{chipCount(chip.key)}</span>
              )}
            </button>
          )
        })}
      </div>

      <div
        className={`rp-dropzone ${dragOver ? 'is-over' : ''}`}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            inputRef.current?.click()
          }
        }}
      >
        <span className="rp-dropzone__icon" aria-hidden>
          <UploadIcon size={28} />
        </span>
        <div className="rp-dropzone__text">
          <strong>Drag and drop files here or click to upload</strong>
          <span>Supports: JPG, PNG, MP4 (max 10MB each)</span>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          onChange={(e) => {
            if (e.target.files) onAddFiles(e.target.files)
            // allow re-selecting the same file
            e.target.value = ''
          }}
        />
      </div>

      {topError && <div className="rp-evidence__error">{topError}</div>}

      {files.length > 0 && (
        <div className="rp-thumbs">
          {files.map((f) => (
            <div key={f.id} className={`rp-thumb ${f.error ? 'has-error' : ''}`}>
              <div className="rp-thumb__preview">
                {f.previewUrl ? (
                  <img src={f.previewUrl} alt="" />
                ) : (
                  <div className="rp-thumb__placeholder" aria-hidden>
                    <FileIcon size={28} />
                  </div>
                )}
                <button
                  type="button"
                  className="rp-thumb__remove"
                  aria-label={`Remove ${f.name}`}
                  onClick={() => onRemoveFile(f.id)}
                >
                  <CloseIcon size={12} />
                </button>
              </div>
              <div className="rp-thumb__meta">
                <span className="rp-thumb__name" title={f.name}>
                  {f.name}
                </span>
                <span className="rp-thumb__size">{formatBytes(f.size)}</span>
                {f.error && <span className="rp-thumb__error">{f.error}</span>}
              </div>
            </div>
          ))}
          <button
            type="button"
            className="rp-thumb rp-thumb--add"
            onClick={() => inputRef.current?.click()}
            aria-label="Add more files"
          >
            <span className="rp-thumb__add-icon" aria-hidden>
              <PlusIcon size={26} />
            </span>
            <span>Add more</span>
          </button>
        </div>
      )}

      <label className="rp-checkbox">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => {
            onConfirmChange(e.target.checked)
            setTopError(null)
          }}
        />
        <span>I confirm that the information provided is accurate.</span>
      </label>

      <div className="rp-wizard__footer">
        <button type="button" className="rp-btn rp-btn--ghost" onClick={onBack}>
          ← Back
        </button>
        <button
          type="button"
          className="rp-btn rp-btn--primary"
          onClick={() => {
            if (!confirmed) {
              setTopError('Please confirm that the information provided is accurate.')
              return
            }
            onNext()
          }}
          disabled={!canNext}
        >
          Next: Review →
        </button>
      </div>
    </div>
  )
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

/* ====================================================================
 * Step 3 — Review
 * ==================================================================== */
interface ReviewStepProps {
  trip: Trip | null
  categoryLabel: string
  claim: string
  evidenceCount: number
  files: FileEntry[]
  onEdit: () => void
  onBack: () => void
  onSubmit: () => void
  onCancel: () => void
  submitting: boolean
  submitError: string | null
}

function ReviewStep({
  trip,
  categoryLabel,
  claim,
  evidenceCount,
  files,
  onEdit,
  onBack,
  onSubmit,
  onCancel,
  submitting,
  submitError,
}: ReviewStepProps) {
  const previews = files.filter((f) => f.previewUrl && !f.error)
  return (
    <div className="rp-wizard__step">
      <h2>Dispute Summary</h2>
      <p className="subtitle">Confirm the details before we start the investigation.</p>

      <div className="rp-card rp-summary">
        <button type="button" className="rp-summary__edit" onClick={onEdit}>
          <PencilIcon size={14} /> Edit
        </button>
        <dl className="rp-summary__list">
          <div>
            <dt>Trip ID</dt>
            <dd>{trip ? `#${trip.id}` : '—'}</dd>
          </div>
          <div>
            <dt>Category</dt>
            <dd>{categoryLabel || '—'}</dd>
          </div>
          <div>
            <dt>Claim</dt>
            <dd>{claim || '—'}</dd>
          </div>
          <div>
            <dt>Evidence</dt>
            <dd>
              {evidenceCount === 0
                ? 'None'
                : `${evidenceCount} file${evidenceCount === 1 ? '' : 's'}`}
            </dd>
          </div>
        </dl>
        {evidenceCount > 0 && (
          <p className="rp-mock-note">
            Evidence images are listed, not analysed, in this version.
          </p>
        )}
      </div>

      {previews.length > 0 && (
        <>
          <h2 className="rp-wizard__h2">Evidence Preview</h2>
          <div className="rp-thumbs rp-thumbs--preview">
            {previews.map((f) => (
              <div key={f.id} className="rp-thumb rp-thumb--preview">
                <div className="rp-thumb__preview">
                  {f.previewUrl ? <img src={f.previewUrl} alt={f.name} /> : null}
                </div>
                <div className="rp-thumb__meta">
                  <span className="rp-thumb__name" title={f.name}>
                    {f.name}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {submitError && <div className="rp-evidence__error">{submitError}</div>}

      <div className="rp-wizard__footer">
        <button type="button" className="rp-btn rp-btn--ghost" onClick={onBack} disabled={submitting}>
          ← Back
        </button>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            type="button"
            className="rp-btn rp-btn--ghost"
            onClick={onCancel}
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="rp-btn rp-btn--primary"
            onClick={onSubmit}
            disabled={submitting}
          >
            {submitting ? 'Submitting…' : 'Submit Dispute →'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ====================================================================
 * Step 4 — Submitting / Confirmation
 * ==================================================================== */
interface SubmittingStepProps {
  trip: Trip
  categoryLabel: string
  claim: string
  fileCount: number
  submitting: boolean
  error: string | null
  onRetry: () => void
}

function SubmittingStep({
  trip,
  categoryLabel,
  claim,
  fileCount,
  submitting,
  error,
  onRetry,
}: SubmittingStepProps) {
  return (
    <div className="rp-wizard__step">
      <h2>Submitting…</h2>
      <p className="subtitle">
        Sending your dispute to the agent pipeline. This usually takes a few seconds.
      </p>
      {error ? (
        <div className="rp-card rp-card--padded">
          <strong>Couldn't submit the dispute.</strong>
          <p>{error}</p>
          <button type="button" className="rp-btn rp-btn--primary" onClick={onRetry}>
            Retry
          </button>
        </div>
      ) : (
        <div className="rp-card rp-card--padded">
          <strong>Trip #{trip.id} · {categoryLabel}</strong>
          <p style={{ whiteSpace: 'pre-wrap' }}>{claim}</p>
          {fileCount > 0 && (
            <p className="rp-mock-note">
              {fileCount} evidence file{fileCount === 1 ? '' : 's'} attached (names only —
              not analysed).
            </p>
          )}
        </div>
      )}
      {!submitting && !error && (
        <p className="rp-muted" style={{ fontSize: 12 }}>
          You will be redirected once the investigation begins.
        </p>
      )}
    </div>
  )
}

/* ====================================================================
 * Trip drawer
 * ==================================================================== */
function TripDrawer({ trip, onClose }: { trip: Trip | null; onClose: () => void }) {
  // close on escape
  useEffect(() => {
    if (!trip) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [trip, onClose])
  if (!trip) return null
  return (
    <div className="rp-drawer-backdrop" onClick={onClose} role="presentation">
      <aside
        className="rp-drawer"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Trip details"
      >
        <header className="rp-drawer__head">
          <h3>Trip #{trip.id}</h3>
          <button type="button" className="rp-drawer__close" onClick={onClose} aria-label="Close">
            <CloseIcon size={14} />
          </button>
        </header>
        <dl className="rp-drawer__list">
          <div>
            <dt>Rider</dt>
            <dd>{trip.rider}</dd>
          </div>
          <div>
            <dt>Driver</dt>
            <dd>{trip.driver}</dd>
          </div>
          <div>
            <dt>Fare</dt>
            <dd>${trip.fare.toFixed(2)}</dd>
          </div>
          <div>
            <dt>Scenario</dt>
            <dd>{trip.scenario}</dd>
          </div>
        </dl>
        <p className="rp-mock-note" style={{ marginTop: 12 }}>
          MOCK: no backend endpoint yet for individual trip summary. The drawer shows the
          fields returned by <code>GET /api/trips</code>.
        </p>
      </aside>
    </div>
  )
}
