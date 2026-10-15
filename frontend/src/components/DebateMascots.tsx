/* ============================================================
 * Three debate mascots — Rider Advocate, Judge, Driver Advocate.
 * Each is a tinted variant of the same red-panda body, so the
 * page reads as one cast of characters rather than three
 * unrelated illustrations.
 * ============================================================ */

interface MascotProps {
  size?: number
  className?: string
}

const RIDER_ACCENT = '#F0246E' // pink
const DRIVER_ACCENT = '#1F64CC' // blue
const JUDGE_ACCENT = '#A25C00' // warm brown (gavel/wood)
const FUR = '#D8531E'
const FUR_DEEP = '#7A2E0F'
const BELLY = '#F7E1C8'

function Panda({ accent, size, className, gavel }: { accent: string; size: number; className?: string; gavel?: boolean }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 160 160"
      fill="none"
      aria-hidden
      role="img"
    >
      <ellipse cx="80" cy="135" rx="48" ry="6" fill="rgba(0,0,0,0.10)" />
      {/* body */}
      <path d="M40 110c0 18 18 30 40 30s40-12 40-30v-8H40v8z" fill={FUR} stroke={FUR_DEEP} strokeWidth="2" strokeLinejoin="round" />
      <ellipse cx="80" cy="118" rx="22" ry="14" fill={BELLY} />
      {/* arms */}
      <path d="M48 100c-6 0-10 4-10 10s4 10 10 10" fill={FUR} stroke={FUR_DEEP} strokeWidth="2" />
      <path d="M118 95c10-2 18-10 18-20 0-3-2-5-5-5s-5 2-5 5c0 4-4 8-10 9" fill={FUR} stroke={FUR_DEEP} strokeWidth="2" strokeLinejoin="round" />
      <circle cx="131" cy="68" r="6" fill={BELLY} stroke={FUR_DEEP} strokeWidth="2" />
      {/* head */}
      <circle cx="80" cy="70" r="36" fill={FUR} stroke={FUR_DEEP} strokeWidth="2" />
      <circle cx="55" cy="44" r="10" fill={FUR} stroke={FUR_DEEP} strokeWidth="2" />
      <circle cx="105" cy="44" r="10" fill={FUR} stroke={FUR_DEEP} strokeWidth="2" />
      <circle cx="55" cy="44" r="5" fill={FUR_DEEP} />
      <circle cx="105" cy="44" r="5" fill={FUR_DEEP} />
      {/* face mask */}
      <ellipse cx="80" cy="76" rx="22" ry="18" fill={BELLY} />
      <circle cx="69" cy="68" r="4" fill="#1B1D24" />
      <circle cx="91" cy="68" r="4" fill="#1B1D24" />
      <circle cx="70" cy="67" r="1.2" fill="#fff" />
      <circle cx="92" cy="67" r="1.2" fill="#fff" />
      <path d="M77 78c0-1.5 1.5-3 3-3s3 1.5 3 3-1.5 3-3 3-3-1.5-3-3z" fill="#1B1D24" />
      <path d="M73 86c2 3 5 4 7 4s5-1 7-4" stroke="#1B1D24" strokeWidth="2" strokeLinecap="round" fill="none" />
      {/* cheek blush in the speaker's accent colour */}
      <circle cx="60" cy="80" r="3" fill={accent} opacity="0.5" />
      <circle cx="100" cy="80" r="3" fill={accent} opacity="0.5" />
      {/* bow-tie / accent strip in the speaker colour */}
      <path
        d="M70 108l-10 4 10 4 10-4 10 4 10-4-10-4 10-4-10-4-10 4-10-4z"
        fill={accent}
        stroke={FUR_DEEP}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      {/* optional gavel for the judge */}
      {gavel && (
        <g transform="translate(20 18) rotate(-22)">
          <rect x="0" y="0" width="22" height="10" rx="2" fill={JUDGE_ACCENT} stroke={FUR_DEEP} strokeWidth="1.5" />
          <rect x="22" y="-4" width="22" height="18" rx="3" fill={BELLY} stroke={FUR_DEEP} strokeWidth="1.5" />
        </g>
      )}
    </svg>
  )
}

export function RiderMascot({ size = 132, className }: MascotProps) {
  return <Panda accent={RIDER_ACCENT} size={size} className={className} />
}

export function DriverMascot({ size = 132, className }: MascotProps) {
  return <Panda accent={DRIVER_ACCENT} size={size} className={className} />
}

export function JudgeMascot({ size = 160, className }: MascotProps) {
  return <Panda accent={JUDGE_ACCENT} size={size} className={className} gavel />
}
