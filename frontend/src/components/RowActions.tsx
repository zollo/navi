import { LuArrowDown, LuArrowUp, LuTrash2 } from "react-icons/lu";

// Up / down / remove buttons for a row in the editor.
export default function RowActions({
  index,
  count,
  onMove,
  onRemove,
  what,
}: {
  index: number;
  count: number;
  onMove: (delta: number) => void;
  onRemove: () => void;
  what: string;
}) {
  return (
    <div className="row-actions">
      <button
        type="button"
        className="icon-btn"
        onClick={() => onMove(-1)}
        disabled={index === 0}
        aria-label={`Move ${what} up`}
      >
        <LuArrowUp aria-hidden />
      </button>
      <button
        type="button"
        className="icon-btn"
        onClick={() => onMove(1)}
        disabled={index === count - 1}
        aria-label={`Move ${what} down`}
      >
        <LuArrowDown aria-hidden />
      </button>
      <button type="button" className="icon-btn danger" onClick={onRemove} aria-label={`Remove ${what}`}>
        <LuTrash2 aria-hidden />
      </button>
    </div>
  );
}
