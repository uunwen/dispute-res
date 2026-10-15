interface Step {
  key: string
  label: string
}

interface StepProgressProps {
  steps: Step[]
  currentKey: string
}

export default function StepProgress({ steps, currentKey }: StepProgressProps) {
  const currentIndex = steps.findIndex((s) => s.key === currentKey)
  return (
    <div
      className="rp-stepper"
      style={{ ['--rp-stepper-count' as never]: steps.length }}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={steps.length}
      aria-valuenow={currentIndex + 1}
    >
      {steps.map((step, idx) => {
        const isComplete = idx < currentIndex
        const isCurrent = idx === currentIndex
        const cls = isComplete ? 'is-complete' : isCurrent ? 'is-current' : ''
        return (
          <div className={`rp-stepper__step ${cls}`} key={step.key}>
            <span className="rp-stepper__bubble">{idx + 1}</span>
            <span className="rp-stepper__label">{step.label}</span>
          </div>
        )
      })}
    </div>
  )
}
