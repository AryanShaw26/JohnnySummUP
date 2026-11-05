import React from 'react';

interface MascotBadgeProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showTagline?: boolean;
  className?: string;
}

export const MascotBadge: React.FC<MascotBadgeProps> = ({
  size = 'md',
  showTagline = false,
  className = '',
}) => {
  const sizeMap = {
    sm: { icon: 28, text: 'text-base', sub: 'text-xs' },
    md: { icon: 38, text: 'text-lg', sub: 'text-xs' },
    lg: { icon: 54, text: 'text-2xl', sub: 'text-sm' },
    xl: { icon: 72, text: 'text-4xl', sub: 'text-base' },
  };

  const dim = sizeMap[size];

  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      {/* Johnny Mascot Detective SVG */}
      <div
        className="relative flex items-center justify-center rounded-2xl bg-gradient-to-br from-[#6257F5] to-[#4c42cf] text-white shadow-md shadow-violet-500/20"
        style={{ width: dim.icon, height: dim.icon }}
      >
        <svg
          viewBox="0 0 48 48"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-3/4 h-3/4"
        >
          {/* Medical document background */}
          <rect x="10" y="8" width="28" height="34" rx="4" fill="white" opacity="0.95" />
          <line x1="16" y1="16" x2="28" y2="16" stroke="#6257F5" strokeWidth="2.5" strokeLinecap="round" />
          <line x1="16" y1="22" x2="32" y2="22" stroke="#22B8B0" strokeWidth="2" strokeLinecap="round" />
          <line x1="16" y1="28" x2="26" y2="28" stroke="#E8E7F0" strokeWidth="2" strokeLinecap="round" />
          
          {/* Detective Magnifier with Teal Lens */}
          <circle cx="28" cy="28" r="9" fill="#22B8B0" fillOpacity="0.25" stroke="#22B8B0" strokeWidth="3" />
          <circle cx="28" cy="28" r="4" fill="#6257F5" />
          <line x1="34.5" y1="34.5" x2="41" y2="41" stroke="#292443" strokeWidth="3.5" strokeLinecap="round" />
        </svg>
        {/* Soft sparkle indicator */}
        <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-[#22B8B0] rounded-full ring-2 ring-white animate-pulse" />
      </div>

      <div>
        <div className={`font-bold tracking-tight text-[#292443] ${dim.text} flex items-center gap-1.5`}>
          Johnny<span className="text-[#6257F5]">SummUP</span>
        </div>
        {showTagline && (
          <p className={`font-medium text-[#77758A] ${dim.sub}`}>
            Your brave medical summarizer 🔍
          </p>
        )}
      </div>
    </div>
  );
};

export default MascotBadge;

