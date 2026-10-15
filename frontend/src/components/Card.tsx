import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  padded?: boolean
  className?: string
}

export default function Card({ children, padded = true, className }: CardProps) {
  return (
    <div className={`rp-card${padded ? ' rp-card--padded' : ''}${className ? ' ' + className : ''}`}>
      {children}
    </div>
  )
}

interface EmptyProps {
  title?: ReactNode
  children?: ReactNode
}

export function Empty({ title, children }: EmptyProps) {
  return (
    <div className="rp-empty">
      {title ? <strong>{title}</strong> : null}
      {children}
    </div>
  )
}
