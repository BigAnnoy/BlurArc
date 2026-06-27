import React, { useId } from 'react';

interface AlbumCoverDefaultProps {
  size: 'tile' | 'cover' | 'thumb';
  className?: string;
}

/**
 * 相册默认封面组件（拍立得堆叠风格，与原型 v3 一致）
 * - 3 张拍立得错落堆叠
 * - 前层完整显示（淡渐变背景 + 山景线条 + 太阳装饰 + 投影）
 * - 后两层逐级淡出
 * - 外框和照片区域均为 4:3
 */
export const AlbumCoverDefault: React.FC<AlbumCoverDefaultProps> = ({ size, className = '' }) => {
  const uid = useId().replace(/:/g, '');
  const shadowId = `shadow-${uid}`;
  const skyId = `sky-${uid}`;

  const sizeConfig = {
    tile: { width: 200, height: 200, viewBox: '0 0 200 200' },
    cover: { width: '100%', height: '100%', viewBox: '0 0 200 150' },
    thumb: { width: 36, height: 36, viewBox: '0 0 200 200' },
  };

  const config = sizeConfig[size];

  return (
    <div className={`album-cover-default ${className}`} style={{ width: config.width, height: config.height }}>
      <svg viewBox={config.viewBox} xmlns="http://www.w3.org/2000/svg" className="w-full h-full" style={{ display: 'block' }}>
        <defs>
          <filter id={shadowId} x="-30%" y="-30%" width="160%" height="160%">
            <feDropShadow dx="0" dy="3" stdDeviation="4" floodColor="#0f172a" floodOpacity="0.18"/>
          </filter>
          <linearGradient id={skyId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#cbd5e1" stopOpacity="0.25"/>
            <stop offset="100%" stopColor="#64748b" stopOpacity="0.18"/>
          </linearGradient>
        </defs>

        {/* 后层拍立得 */}
        <g transform="rotate(-16 50 65)" opacity="0.32">
          <rect x="10" y="35" width="80" height="60" rx="3" fill="var(--bg-card)" stroke="var(--stroke-light)" strokeWidth="1.2"/>
        </g>

        {/* 中层拍立得 */}
        <g transform="rotate(11 140 80)" opacity="0.58">
          <rect x="100" y="50" width="80" height="60" rx="3" fill="var(--bg-card)" stroke="var(--stroke)" strokeWidth="1.2"/>
        </g>

        {/* 前层拍立得（4:3 外框 + 4:3 照片 + 投影） */}
        <g transform="rotate(-4 100 100)" filter={`url(#${shadowId})`}>
          <rect x="50" y="55" width="100" height="75" rx="3.5" fill="var(--bg-card)" stroke="var(--stroke-strong)" strokeWidth="1.4"/>
          <rect x="58" y="61" width="84" height="63" fill={`url(#${skyId})`}/>
          <rect x="58" y="61" width="84" height="63" fill="none" stroke="var(--stroke-light)" strokeWidth="0.8"/>
          <path d="M58 124 L74 104 L86 112 L100 96 L114 108 L128 90 L142 124"
                stroke="var(--stroke-strong)" strokeWidth="1.3" fill="none" strokeLinejoin="round" strokeLinecap="round"/>
          <circle cx="124" cy="76" r="6" stroke="var(--stroke-strong)" strokeWidth="1.3" fill="none"/>
          <line x1="133" y1="76" x2="137" y2="76" stroke="var(--stroke-strong)" strokeWidth="1.3"/>
          <line x1="130.36" y1="82.36" x2="133.19" y2="85.19" stroke="var(--stroke-strong)" strokeWidth="1.3"/>
          <line x1="124" y1="85" x2="124" y2="89" stroke="var(--stroke-strong)" strokeWidth="1.3"/>
          <line x1="117.64" y1="82.36" x2="114.81" y2="85.19" stroke="var(--stroke-strong)" strokeWidth="1.3"/>
          <line x1="115" y1="76" x2="111" y2="76" stroke="var(--stroke-strong)" strokeWidth="1.3"/>
          <line x1="117.64" y1="69.64" x2="114.81" y2="66.81" stroke="var(--stroke-strong)" strokeWidth="1.3"/>
          <line x1="124" y1="67" x2="124" y2="63" stroke="var(--stroke-strong)" strokeWidth="1.3"/>
          <line x1="130.36" y1="69.64" x2="133.19" y2="66.81" stroke="var(--stroke-strong)" strokeWidth="1.3"/>
        </g>
      </svg>
    </div>
  );
};
