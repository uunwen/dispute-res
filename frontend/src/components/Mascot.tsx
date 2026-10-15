interface MascotProps {
  size?: number
  className?: string
}

/**
 * Friendly red-panda waving mascot used in the Dashboard welcome card.
 * Pure inline SVG so no external image asset is required and it scales
 * crisply. NOT a real photo — purely decorative.
 */
export default function Mascot({ size = 140, className }: MascotProps) {
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
      {/* Background blob */}
      <ellipse cx="80" cy="135" rx="48" ry="6" fill="rgba(0,0,0,0.10)" />

      {/* Body */}
      <path
        d="M40 110c0 18 18 30 40 30s40-12 40-30v-8H40v8z"
        fill="#D8531E"
      />
      <path
        d="M40 110c0 18 18 30 40 30s40-12 40-30v-8H40v8z"
        fill="url(#bodyShade)"
        opacity="0.35"
      />

      {/* Belly */}
      <ellipse cx="80" cy="118" rx="22" ry="14" fill="#F7E1C8" />

      {/* Waving arm (right) */}
      <path
        d="M118 95c10-2 18-10 18-20 0-3-2-5-5-5s-5 2-5 5c0 4-4 8-10 9"
        fill="#D8531E"
        stroke="#7A2E0F"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <circle cx="131" cy="68" r="6" fill="#F7E1C8" stroke="#7A2E0F" strokeWidth="2" />

      {/* Other arm tucked in */}
      <path
        d="M48 100c-6 0-10 4-10 10s4 10 10 10"
        fill="#D8531E"
        stroke="#7A2E0F"
        strokeWidth="2"
        strokeLinejoin="round"
      />

      {/* Head */}
      <circle cx="80" cy="70" r="36" fill="#D8531E" stroke="#7A2E0F" strokeWidth="2" />

      {/* Ears */}
      <circle cx="55" cy="44" r="10" fill="#D8531E" stroke="#7A2E0F" strokeWidth="2" />
      <circle cx="105" cy="44" r="10" fill="#D8531E" stroke="#7A2E0F" strokeWidth="2" />
      <circle cx="55" cy="44" r="5" fill="#7A2E0F" />
      <circle cx="105" cy="44" r="5" fill="#7A2E0F" />

      {/* Face mask (white) */}
      <ellipse cx="80" cy="76" rx="22" ry="18" fill="#F7E1C8" />

      {/* Eyes */}
      <circle cx="69" cy="68" r="4" fill="#1B1D24" />
      <circle cx="91" cy="68" r="4" fill="#1B1D24" />
      <circle cx="70" cy="67" r="1.2" fill="#fff" />
      <circle cx="92" cy="67" r="1.2" fill="#fff" />

      {/* Nose */}
      <path
        d="M77 78c0-1.5 1.5-3 3-3s3 1.5 3 3-1.5 3-3 3-3-1.5-3-3z"
        fill="#1B1D24"
      />

      {/* Smile */}
      <path
        d="M73 86c2 3 5 4 7 4s5-1 7-4"
        stroke="#1B1D24"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />

      {/* Cheek blush */}
      <circle cx="60" cy="80" r="3" fill="#F0246E" opacity="0.5" />
      <circle cx="100" cy="80" r="3" fill="#F0246E" opacity="0.5" />

      <defs>
        <linearGradient id="bodyShade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity="0.25" />
        </linearGradient>
      </defs>
    </svg>
  )
}
