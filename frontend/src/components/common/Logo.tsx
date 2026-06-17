export function Logo({ size = 24 }: { size?: number }) {
  const gradId = `logoArc-${size}`;
  const glowId = `logoGlow-${size}`;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 40 40"
      style={{ color: '#0891b2' }}
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0891b2" stopOpacity="0.95" />
          <stop offset="1" stopColor="#06b6d4" stopOpacity="0.65" />
        </linearGradient>
        <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="1.5" />
        </filter>
      </defs>
      <circle
        cx="20" cy="20" r="14"
        stroke="#22d3ee"
        strokeWidth="3.5"
        fill="none"
        strokeDasharray="55 33"
        strokeLinecap="round"
        transform="rotate(-30 20 20)"
        filter={`url(#${glowId})`}
        opacity="0.3"
      />
      <circle
        cx="20" cy="20" r="14"
        stroke={`url(#${gradId})`}
        strokeWidth="2.2"
        fill="none"
        strokeDasharray="55 33"
        strokeLinecap="round"
        transform="rotate(-30 20 20)"
      />
      <circle
        cx="20" cy="20" r="8"
        stroke="#0891b2"
        strokeWidth="1.6"
        fill="none"
        strokeDasharray="28 22"
        strokeLinecap="round"
        transform="rotate(60 20 20)"
        opacity="0.75"
      />
      <circle cx="20" cy="20" r="2" fill="#0891b2" filter={`url(#${glowId})`} opacity="0.6" />
      <circle cx="20" cy="20" r="1.4" fill="#0891b2" />
    </svg>
  );
}
