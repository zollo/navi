import { describe, expect, it } from "vitest";
import { ApiError, errorMessage } from "./client";

describe("ApiError", () => {
  it("carries a status code and message", () => {
    const err = new ApiError(404, "Not found");
    expect(err.status).toBe(404);
    expect(err.message).toBe("Not found");
    expect(err).toBeInstanceOf(Error);
  });
});

describe("errorMessage", () => {
  it("uses a string detail", () => {
    expect(errorMessage({ detail: "Nope" }, "fallback")).toBe("Nope");
  });

  it("flattens FastAPI validation errors", () => {
    const data = {
      detail: [{ loc: ["body", "url"], msg: "Value error, must start with https://, http:// or mailto:" }],
    };
    expect(errorMessage(data, "fallback")).toBe(
      "url: Value error, must start with https://, http:// or mailto:",
    );
  });

  it("falls back when there is no detail", () => {
    expect(errorMessage(null, "fallback")).toBe("fallback");
  });
});
