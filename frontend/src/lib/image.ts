// Browser-side image helpers: shrink an upload to fit the server's size limit,
// and tell whether an image is mostly dark.

const MAX_SIDE = 2400;

function loadImage(file: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("That file isn't an image this browser can read"));
    };
    img.src = url;
  });
}

function encode(canvas: HTMLCanvasElement, type: string, quality: number): Promise<Blob | null> {
  return new Promise((resolve) => canvas.toBlob(resolve, type, quality));
}

// Return `file` as is if it already fits, else a re-encoded, scaled-down WebP
// (or JPEG where WebP encoding isn't supported) of at most `maxBytes`.
// GIFs are left alone so animation survives; the server rejects them if too big.
export async function fitImage(file: File, maxBytes: number): Promise<File> {
  if (file.type === "image/gif") return file;
  const img = await loadImage(file);
  if (file.size <= maxBytes && Math.max(img.naturalWidth, img.naturalHeight) <= MAX_SIDE) {
    return file;
  }
  let scale = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight));
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  if (!ctx) return file;
  for (let attempt = 0; attempt < 8; attempt++) {
    canvas.width = Math.max(1, Math.round(img.naturalWidth * scale));
    canvas.height = Math.max(1, Math.round(img.naturalHeight * scale));
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    for (const quality of [0.86, 0.75, 0.62]) {
      let blob = await encode(canvas, "image/webp", quality);
      if (!blob || blob.type !== "image/webp") blob = await encode(canvas, "image/jpeg", quality);
      if (blob && blob.size <= maxBytes) {
        const ext = blob.type === "image/webp" ? "webp" : "jpg";
        const name = file.name.replace(/\.[^.]+$/, "") + "." + ext;
        return new File([blob], name, { type: blob.type });
      }
    }
    scale *= 0.75;
  }
  throw new Error("Couldn't make the image small enough. Try a smaller one.");
}

// Whether an image is mostly dark, from its average luminance.
export async function imageIsDark(file: Blob): Promise<boolean> {
  try {
    const img = await loadImage(file);
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 24;
    const ctx = canvas.getContext("2d");
    if (!ctx) return true;
    ctx.drawImage(img, 0, 0, 24, 24);
    const { data } = ctx.getImageData(0, 0, 24, 24);
    let sum = 0;
    for (let i = 0; i < data.length; i += 4) {
      sum += 0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2];
    }
    return sum / (data.length / 4) < 140;
  } catch {
    return true;
  }
}
