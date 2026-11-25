import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type WheelEvent } from "react";
import { LuFlipHorizontal2, LuRotateCcw, LuRotateCw, LuUndo2, LuZoomIn, LuZoomOut } from "react-icons/lu";
import {
  clampEdit,
  draw,
  encodeUnderLimit,
  formatKb,
  initialEdit,
  MAX_ZOOM,
  MIN_ZOOM,
  rotate,
  zoomAt,
  type Edit,
} from "../lib/avatar";

interface Props {
  image: HTMLImageElement;
  animated: boolean; // a GIF: editing keeps only its first frame
  maxBytes: number;
  onCancel: () => void;
  onSave: (file: File) => Promise<void>;
}

// Modal photo editor: drag to reposition, pinch / scroll / slider to zoom, rotate
// and flip, then the result is shrunk until it fits under the upload limit.
export default function AvatarEditor({ image, animated, maxBytes, onCancel, onSave }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [edit, setEdit] = useState<Edit>(initialEdit);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const w = image.naturalWidth;
  const h = image.naturalHeight;

  const change = useCallback((f: (e: Edit) => Edit) => setEdit((e) => f(e)), []);

  useEffect(() => {
    const d = dialogRef.current;
    if (d && !d.open) d.showModal();
  }, []);

  // Redraw the preview at device resolution whenever the edit changes.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const css = canvas.clientWidth || 280;
    const px = Math.round(css * (window.devicePixelRatio || 1));
    if (canvas.width !== px) canvas.width = canvas.height = px;
    const ctx = canvas.getContext("2d");
    if (ctx) draw(ctx, image, edit, px);
  }, [edit, image]);

  // Pointer position in viewport units relative to the centre.
  const toViewport = (clientX: number, clientY: number): [number, number] => {
    const r = canvasRef.current!.getBoundingClientRect();
    return [(clientX - r.left) / r.width - 0.5, (clientY - r.top) / r.height - 0.5];
  };

  const onPointerDown = (e: PointerEvent<HTMLCanvasElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
  };

  const onPointerMove = (e: PointerEvent<HTMLCanvasElement>) => {
    const map = pointers.current;
    const prev = map.get(e.pointerId);
    if (!prev) return;
    const size = e.currentTarget.getBoundingClientRect().width || 1;
    if (map.size === 1) {
      const dx = (e.clientX - prev.x) / size;
      const dy = (e.clientY - prev.y) / size;
      change((s) => clampEdit(w, h, { ...s, x: s.x + dx, y: s.y + dy }));
    } else if (map.size === 2) {
      // Pinch: zoom by the change in finger distance, around their midpoint.
      const other = [...map.entries()].find(([id]) => id !== e.pointerId)![1];
      const before = Math.hypot(prev.x - other.x, prev.y - other.y);
      const after = Math.hypot(e.clientX - other.x, e.clientY - other.y);
      if (before > 0) {
        const [px, py] = toViewport((e.clientX + other.x) / 2, (e.clientY + other.y) / 2);
        change((s) => zoomAt(w, h, s, after / before, px, py));
      }
    }
    map.set(e.pointerId, { x: e.clientX, y: e.clientY });
  };

  const onPointerUp = (e: PointerEvent<HTMLCanvasElement>) => {
    pointers.current.delete(e.pointerId);
  };

  const onWheel = (e: WheelEvent<HTMLCanvasElement>) => {
    const [px, py] = toViewport(e.clientX, e.clientY);
    change((s) => zoomAt(w, h, s, Math.exp(-e.deltaY * 0.0015), px, py));
  };

  const onKeyDown = (e: KeyboardEvent<HTMLCanvasElement>) => {
    const step = e.shiftKey ? 0.1 : 0.02;
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [-step, 0],
      ArrowRight: [step, 0],
      ArrowUp: [0, -step],
      ArrowDown: [0, step],
    };
    if (moves[e.key]) {
      const [dx, dy] = moves[e.key];
      change((s) => clampEdit(w, h, { ...s, x: s.x + dx, y: s.y + dy }));
    } else if (e.key === "+" || e.key === "=") {
      change((s) => zoomAt(w, h, s, 1.1));
    } else if (e.key === "-") {
      change((s) => zoomAt(w, h, s, 1 / 1.1));
    } else {
      return;
    }
    e.preventDefault();
  };

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const canvas = document.createElement("canvas");
      const encoded = await encodeUnderLimit(async (size, type, quality) => {
        canvas.width = canvas.height = size;
        const ctx = canvas.getContext("2d");
        if (!ctx) return null;
        // JPEG has no transparency: put transparent areas on white, not black.
        draw(ctx, image, edit, size, type === "image/jpeg" ? "#ffffff" : undefined);
        return new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, type, quality));
      }, maxBytes);
      const ext = encoded.blob.type === "image/webp" ? "webp" : "jpg";
      await onSave(new File([encoded.blob], `avatar.${ext}`, { type: encoded.blob.type }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save the photo");
      setBusy(false);
    }
  };

  return (
    <dialog
      ref={dialogRef}
      className="avatar-editor"
      aria-labelledby="avatar-editor-title"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onCancel();
      }}
    >
      <h2 id="avatar-editor-title">Edit photo</h2>
      <p className="muted small-print">
        Drag to reposition. Pinch, scroll or use the slider to zoom. The circle shows what visitors see.
      </p>

      <div className="crop-frame">
        <canvas
          ref={canvasRef}
          className="crop-canvas"
          tabIndex={0}
          role="img"
          aria-label="Photo preview. Use arrow keys to move and plus or minus to zoom."
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onWheel={onWheel}
          onKeyDown={onKeyDown}
        />
        <div className="crop-mask" aria-hidden />
      </div>

      <div className="crop-zoom">
        <button type="button" className="btn ghost icon" aria-label="Zoom out" onClick={() => change((s) => zoomAt(w, h, s, 1 / 1.2))}>
          <LuZoomOut aria-hidden />
        </button>
        <input
          type="range"
          aria-label="Zoom"
          min={MIN_ZOOM}
          max={MAX_ZOOM}
          step={0.01}
          value={edit.zoom}
          onChange={(e) => {
            const z = Number(e.target.value);
            change((s) => zoomAt(w, h, s, z / s.zoom));
          }}
        />
        <button type="button" className="btn ghost icon" aria-label="Zoom in" onClick={() => change((s) => zoomAt(w, h, s, 1.2))}>
          <LuZoomIn aria-hidden />
        </button>
      </div>

      <div className="crop-tools">
        <button type="button" className="btn secondary small" onClick={() => change((s) => rotate(w, h, s, -1))}>
          <LuRotateCcw aria-hidden /> Rotate left
        </button>
        <button type="button" className="btn secondary small" onClick={() => change((s) => rotate(w, h, s, 1))}>
          <LuRotateCw aria-hidden /> Rotate right
        </button>
        <button
          type="button"
          className="btn secondary small"
          aria-pressed={edit.flip}
          onClick={() => change((s) => ({ ...s, flip: !s.flip, x: -s.x }))}
        >
          <LuFlipHorizontal2 aria-hidden /> Flip
        </button>
        <button type="button" className="btn ghost small" onClick={() => setEdit(initialEdit())}>
          <LuUndo2 aria-hidden /> Reset
        </button>
      </div>

      {animated && <div className="alert info">Animated GIFs are saved as a still image of the first frame.</div>}
      {error && <div className="alert error">{error}</div>}

      <div className="dialog-actions">
        <span className="muted small-print">Saved as a square photo up to 512 px, under {formatKb(maxBytes)}.</span>
        <button type="button" className="btn secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button type="button" className="btn" onClick={save} disabled={busy}>
          {busy ? "Saving…" : "Save photo"}
        </button>
      </div>
    </dialog>
  );
}
