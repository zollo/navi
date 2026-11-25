import { useId } from "react";

// The Navi mark: a four-point compass star crossed by a link, on a violet
// rounded square. Same artwork as public/favicon.svg.
export default function Logo({ size = 28 }: { size?: number }) {
  // Several logos can share a page, so each gets its own gradient id.
  const id = `navi-logo-${useId().replace(/:/g, "")}`;
  const fill = `url(#${id})`;
  return (
    <svg width={size} height={size} viewBox="0 0 512 512" aria-hidden focusable="false" className="navi-logo">
      <defs>
        <linearGradient id={id} x1="0" y1="512" x2="512" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#211a6b" />
          <stop offset="0.5" stopColor="#4c1fa6" />
          <stop offset="1" stopColor="#7d1fc6" />
        </linearGradient>
      </defs>
      <rect width="512" height="512" rx="112" fill={fill} />
      <path d="M256 60L202 202 256 256zM452 256L310 202 256 256zM256 452L310 310 256 256zM60 256L202 310 256 256z" fill="#e2d9f3" />
      <path d="M256 60L310 202 256 256zM452 256L310 310 256 256zM256 452L202 310 256 256zM60 256L202 202 256 256z" fill="#fff" />
      <g fill="none" strokeLinejoin="round">
        <path d={LINK} stroke={fill} strokeWidth="38" />
        <path d={LINK} stroke="#fff" strokeWidth="20" />
      </g>
    </svg>
  );
}

// The link: two hooks joined by a stepped bar, outlined in the tile's gradient
// so it reads as passing over the star.
const LINK =
  "M304 174L328 150A30 30 0 0 1 370 192L290 272Q278 284 266 272L246 252Q234 240 222 252L138 336A30 30 0 0 0 180 378L204 354";
