import { describe, expect, it } from "vitest";
import {
  clampEdit,
  encodeUnderLimit,
  extent,
  initialEdit,
  MAX_ZOOM,
  OUTPUT_SIZES,
  QUALITIES,
  rotate,
  zoomAt,
  type Encoder,
} from "./avatar";

describe("crop math", () => {
  it("covers the square with the short side at zoom 1", () => {
    expect(extent(800, 400, { zoom: 1, rotation: 0 })).toEqual([2, 1]);
    expect(extent(800, 400, { zoom: 1, rotation: 90 })).toEqual([1, 2]);
    expect(extent(800, 400, { zoom: 2, rotation: 0 })).toEqual([4, 2]);
  });

  it("never lets an edge inside the square", () => {
    const e = clampEdit(800, 400, { ...initialEdit(), x: 5, y: 5 });
    expect(e.x).toBe(0.5);
    expect(e.y).toBe(0);
    expect(clampEdit(800, 400, { ...initialEdit(), zoom: 99 }).zoom).toBe(MAX_ZOOM);
    expect(clampEdit(800, 400, { ...initialEdit(), zoom: 0.2 }).zoom).toBe(1);
  });

  it("carries the pan through a rotation and back", () => {
    const start = clampEdit(400, 400, { ...initialEdit(), zoom: 2, x: 0.3, y: -0.1 });
    const right = rotate(400, 400, start, 1);
    expect(right.rotation).toBe(90);
    expect(right.x).toBeCloseTo(0.1);
    expect(right.y).toBeCloseTo(0.3);
    const back = rotate(400, 400, right, -1);
    expect(back.rotation).toBe(0);
    expect(back.x).toBeCloseTo(0.3);
    expect(back.y).toBeCloseTo(-0.1);
    expect(rotate(400, 400, initialEdit(), -1).rotation).toBe(270);
  });

  it("turns the other way in the image's frame when flipped", () => {
    expect(rotate(400, 400, { ...initialEdit(), flip: true }, 1).rotation).toBe(270);
  });

  it("zooms around the given point", () => {
    // The spot under the cursor stays put, so the image centre moves away from it.
    const e = zoomAt(400, 400, initialEdit(), 2, 0.25, 0);
    expect(e.zoom).toBe(2);
    expect(e.x).toBeCloseTo(-0.25);
    expect(e.y).toBe(0);
  });
});

// An encoder whose output size grows with dimensions and quality.
function fakeEncoder(webp: boolean, bytesAt: (size: number, quality: number) => number): Encoder {
  return async (size, type, quality) => {
    const out = type === "image/webp" && !webp ? "image/png" : type;
    return new Blob([new Uint8Array(bytesAt(size, quality))], { type: out });
  };
}

describe("encodeUnderLimit", () => {
  it("keeps full size and quality when it already fits", async () => {
    const r = await encodeUnderLimit(fakeEncoder(true, () => 1000), 2000);
    expect(r).toMatchObject({ size: OUTPUT_SIZES[0], quality: QUALITIES[0] });
    expect(r.blob.type).toBe("image/webp");
  });

  it("lowers quality before dimensions", async () => {
    const r = await encodeUnderLimit(fakeEncoder(true, (s, q) => Math.round(s * s * q * 0.1)), 20000);
    expect(r.size).toBe(512);
    expect(r.quality).toBeLessThan(QUALITIES[0]);
    expect(r.blob.size).toBeLessThanOrEqual(20000);
  });

  it("drops dimensions when quality alone isn't enough", async () => {
    const r = await encodeUnderLimit(fakeEncoder(true, (s, q) => Math.round(s * s * q * 0.1)), 5000);
    expect(r.size).toBeLessThan(512);
    expect(r.blob.size).toBeLessThanOrEqual(5000);
  });

  it("falls back to JPEG where WebP encoding isn't supported", async () => {
    const r = await encodeUnderLimit(fakeEncoder(false, () => 100), 2000);
    expect(r.blob.type).toBe("image/jpeg");
  });

  it("explains when nothing fits", async () => {
    await expect(encodeUnderLimit(fakeEncoder(true, () => 9999), 4096)).rejects.toThrow(/under 4 KB/);
  });
});
