import { useState } from "react";

interface BrandLogoProps {
  compact?: boolean;
  className?: string;
}

export function BrandLogo({ compact = false, className = "" }: BrandLogoProps) {
  const [imageUnavailable, setImageUnavailable] = useState(false);

  return (
    <span className={`brand-lockup ${compact ? "brand-lockup--compact" : ""} ${className}`}>
      {!imageUnavailable && (
        <img
          className="brand-lockup__image"
          src="/brand/johnnysummup-mascot.png"
          alt="JohnnySummUP mascot"
          onError={() => setImageUnavailable(true)}
        />
      )}
      <span className="brand-lockup__text">
        <span className="brand-lockup__name">JohnnySummUP</span>
        {!compact && <span className="brand-lockup__tagline">Your brave summarizer</span>}
      </span>
    </span>
  );
}
