// The Navi mark: a four-point compass star. Same artwork as public/favicon.svg.
export default function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden focusable="false">
      <rect width="64" height="64" rx="16" fill="var(--logo-bg, #4f46e5)" />
      <path d="M32 10l6 16 16 6-16 6-6 16-6-16-16-6 16-6z" fill="#fff" />
      <circle cx="32" cy="32" r="4" fill="var(--logo-bg, #4f46e5)" />
    </svg>
  );
}
