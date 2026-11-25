// The Navi mark: a compass star with a chain link on a purple rounded square.
// Same artwork as the favicon and app icons in public/ (public/icons/*).
export default function Logo({ size = 28 }: { size?: number }) {
  return <img className="logo" src="/icons/logo-256.png" width={size} height={size} alt="" aria-hidden draggable={false} />;
}
