// Avatar editing: the crop math behind the editor, and encoding the result small
// enough for the API. Kept free of React and the DOM where possible so it can be
// unit tested.

// What the person has done to the image. Offsets are in viewport units (1 = the
// crop square's width), so the same edit renders at any canvas size.
export interface Edit {
  zoom: number; // 1 = the image just covers the square
  rotation: 0 | 90 | 180 | 270;
  flip: boolean;
  x: number;
  y: number;
}

export const MIN_ZOOM = 1;
export const MAX_ZOOM = 4;
export const OUTPUT_SIZES = [512, 384, 256, 192, 128];
export const QUALITIES = [0.9, 0.82, 0.74, 0.66, 0.58, 0.5];
export const DEFAULT_MAX_AVATAR_KB = 1024;

export const initialEdit = (): Edit => ({ zoom: 1, rotation: 0, flip: false, x: 0, y: 0 });

// Image size once rotated.
export function rotatedSize(w: number, h: number, rotation: Edit["rotation"]): [number, number] {
  return rotation % 180 === 0 ? [w, h] : [h, w];
}

// How big the (rotated, zoomed) image is, in viewport units. The shorter side
// is exactly 1 at zoom 1, so the image always covers the crop square.
export function extent(w: number, h: number, e: Pick<Edit, "zoom" | "rotation">): [number, number] {
  const [rw, rh] = rotatedSize(w, h, e.rotation);
  const s = e.zoom / Math.min(rw, rh);
  return [rw * s, rh * s];
}

// Keep the image covering the square: never let an edge come inside it.
export function clampEdit(w: number, h: number, e: Edit): Edit {
  const zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, e.zoom));
  const [ew, eh] = extent(w, h, { ...e, zoom });
  const limX = (ew - 1) / 2;
  const limY = (eh - 1) / 2;
  const clamp = (v: number, lim: number) => Math.min(lim, Math.max(-lim, v));
  return { ...e, zoom, x: clamp(e.x, limX), y: clamp(e.y, limY) };
}

// Rotate a quarter turn on screen (1 = clockwise). Rotating swaps the axes, so
// carry the pan across with the image. The mirror is applied after rotation, so
// a flipped image turns the other way in its own frame.
export function rotate(w: number, h: number, e: Edit, dir: 1 | -1): Edit {
  const turn = e.flip ? -dir : dir;
  const rotation = ((((e.rotation + turn * 90) % 360) + 360) % 360) as Edit["rotation"];
  const [x, y] = dir === 1 ? [-e.y, e.x] : [e.y, -e.x];
  return clampEdit(w, h, { ...e, rotation, x, y });
}

// Zoom by a factor around a point in viewport units (0,0 = centre), so the spot
// under the cursor or between the fingers stays put.
export function zoomAt(w: number, h: number, e: Edit, factor: number, px = 0, py = 0): Edit {
  const zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, e.zoom * factor));
  const k = zoom / e.zoom;
  return clampEdit(w, h, { ...e, zoom, x: px - (px - e.x) * k, y: py - (py - e.y) * k });
}

type Drawable = CanvasImageSource & { width: number; height: number };

// Draw the edited image into a size×size square of a 2D context.
export function draw(
  ctx: CanvasRenderingContext2D,
  img: Drawable,
  e: Edit,
  size: number,
  background?: string,
): void {
  const w = img.width;
  const h = img.height;
  ctx.save();
  ctx.clearRect(0, 0, size, size);
  if (background) {
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, size, size);
  }
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  const s = (e.zoom / Math.min(...rotatedSize(w, h, e.rotation))) * size;
  ctx.translate(size / 2 + e.x * size, size / 2 + e.y * size);
  // Flip in screen space, so "Flip" is always a left-right mirror.
  if (e.flip) ctx.scale(-1, 1);
  ctx.rotate((e.rotation * Math.PI) / 180);
  ctx.drawImage(img, (-w * s) / 2, (-h * s) / 2, w * s, h * s);
  ctx.restore();
}

export type Encoder = (size: number, type: string, quality: number) => Promise<Blob | null>;

export interface Encoded {
  blob: Blob;
  size: number; // output width/height in px
  quality: number;
}

// Find the best-looking encoding under maxBytes: largest dimensions first, and at
// each size the highest quality that fits. WebP where the browser can encode it
// (Safari falls back to PNG, which we detect), else JPEG.
export async function encodeUnderLimit(encode: Encoder, maxBytes: number): Promise<Encoded> {
  const probe = await encode(OUTPUT_SIZES[0], "image/webp", QUALITIES[0]);
  const type = probe?.type === "image/webp" ? "image/webp" : "image/jpeg";
  let smallest: Encoded | null = null;
  for (const size of OUTPUT_SIZES) {
    for (const quality of QUALITIES) {
      const blob =
        size === OUTPUT_SIZES[0] && quality === QUALITIES[0] && type === "image/webp" && probe
          ? probe
          : await encode(size, type, quality);
      if (!blob) continue;
      const out = { blob, size, quality };
      if (blob.size <= maxBytes) return out;
      if (!smallest || blob.size < smallest.blob.size) smallest = out;
    }
  }
  const kb = Math.ceil(maxBytes / 1024);
  throw new Error(
    smallest
      ? `Couldn't shrink this photo under ${kb} KB. Try zooming in on a simpler area.`
      : "This browser couldn't save the edited photo.",
  );
}

export function formatKb(bytes: number): string {
  return bytes < 1024 ? `${bytes} B` : `${Math.round(bytes / 1024)} KB`;
}

// Read a picked or dropped file into an image the canvas can draw. Browsers
// apply EXIF orientation, so phone photos come out upright.
export function loadImage(src: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(src);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("This browser can't open that file. Try a JPEG, PNG or WebP image."));
    };
    img.src = url;
  });
}
