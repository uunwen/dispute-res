interface PlaybackBarProps {
  isPlaying: boolean
  onTogglePlay: () => void
  speed: number
  onSpeedChange: (s: number) => void
  progress: number /* 0..1 */
  onSeek: (fraction: number) => void
  /** Label shown next to the progress bar, e.g. "Round 2 of 5 — Driver opening argument" */
  stepLabel: string
  /** Elapsed time, mm:ss */
  elapsedLabel: string
  /** Total time, mm:ss */
  totalLabel: string
  /** When true, the timeline is locked (a round is still typing) */
  scrubbingDisabled?: boolean
}

const SPEEDS = [1, 1.5, 2]

export default function PlaybackBar({
  isPlaying,
  onTogglePlay,
  speed,
  onSpeedChange,
  progress,
  onSeek,
  stepLabel,
  elapsedLabel,
  totalLabel,
  scrubbingDisabled,
}: PlaybackBarProps) {
  return (
    <div className="rp-playback">
      <button
        type="button"
        className={`rp-playback__play ${isPlaying ? 'is-playing' : 'is-paused'}`}
        onClick={onTogglePlay}
        aria-label={isPlaying ? 'Pause' : 'Play'}
      >
        {isPlaying ? (
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
            <rect x="3" y="2" width="3" height="10" rx="1" fill="currentColor" />
            <rect x="8" y="2" width="3" height="10" rx="1" fill="currentColor" />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
            <path d="M3 2l9 5-9 5V2z" fill="currentColor" />
          </svg>
        )}
      </button>

      <div className="rp-playback__speed" role="radiogroup" aria-label="Playback speed">
        {SPEEDS.map((s) => (
          <button
            type="button"
            key={s}
            role="radio"
            aria-checked={s === speed}
            className={`rp-playback__speed-btn ${s === speed ? 'is-active' : ''}`}
            onClick={() => onSpeedChange(s)}
          >
            {s}x
          </button>
        ))}
      </div>

      <div className="rp-playback__progress">
        <div className="rp-playback__step">{stepLabel}</div>
        <div className="rp-playback__track">
          <div
            className="rp-playback__track-fill"
            style={{ width: `${Math.min(100, Math.max(0, progress * 100))}%` }}
          />
          <input
            type="range"
            min={0}
            max={1000}
            value={Math.round(progress * 1000)}
            onChange={(e) => onSeek(Number(e.target.value) / 1000)}
            disabled={scrubbingDisabled}
            aria-label="Seek"
            className="rp-playback__seek"
          />
        </div>
        <div className="rp-playback__time">
          <span>{elapsedLabel}</span>
          <span aria-hidden> / </span>
          <span>{totalLabel}</span>
        </div>
      </div>
    </div>
  )
}
