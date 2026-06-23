import { useTheme } from '../../hooks/useTheme';

export function Logo({ size = 24 }: { size?: number }) {
  const { theme } = useTheme();
  const isDark =
    theme === 'dark' ||
    (theme === 'system' &&
      document.documentElement.classList.contains('dark'));
  const tint = isDark ? '#22d3ee' : '#0891b2';
  const gradId = `logoArc-${size}`;
  const glowId = `logoGlow-${size}`;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="-12 -12 64 64"
      style={{ color: tint }}
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="currentColor" stopOpacity="0.95" />
          <stop offset="1" stopColor="currentColor" stopOpacity="0.65" />
        </linearGradient>
        <filter id={glowId} x="-200%" y="-200%" width="500%" height="500%">
          <feGaussianBlur stdDeviation="2" />
        </filter>
      </defs>
      {/* 光晕层 */}
      <circle
        cx="20" cy="20" r="14"
        stroke="currentColor"
        strokeWidth="3.5"
        fill="none"
        strokeDasharray="55 33"
        strokeLinecap="round"
        transform="rotate(-30 20 20)"
        filter={`url(#${glowId})`}
        opacity="0.3"
      />
      {/* 主弧（渐变） */}
      <circle
        cx="20" cy="20" r="14"
        stroke={`url(#${gradId})`}
        strokeWidth="2.2"
        fill="none"
        strokeDasharray="55 33"
        strokeLinecap="round"
        transform="rotate(-30 20 20)"
      />
      {/* 内弧 */}
      <circle
        cx="20" cy="20" r="8"
        stroke="currentColor"
        strokeWidth="1.6"
        fill="none"
        strokeDasharray="28 22"
        strokeLinecap="round"
        transform="rotate(60 20 20)"
        opacity="0.75"
      />
      {/* 中心点光晕 */}
      <circle cx="20" cy="20" r="2" fill="currentColor" filter={`url(#${glowId})`} opacity="0.6" />
      {/* 中心点实心 */}
      <circle cx="20" cy="20" r="1.4" fill="currentColor" />
    </svg>
  );
}
