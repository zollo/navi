import { describe, expect, it } from "vitest";
import { guessIcon } from "./icons";
import {
  applyImport,
  blankPage,
  dataUrlToFile,
  handleProblem,
  isSafeUrl,
  move,
  normalizeHandle,
  toInput,
} from "./page";

describe("handles", () => {
  it("normalizes", () => {
    expect(normalizeHandle(" @The.SaaSy.Engineer ")).toBe("the.saasy.engineer");
  });

  it("accepts valid handles", () => {
    for (const h of ["abc", "the.saasy.engineer", "a_b-c", "x1y"]) {
      expect(handleProblem(h)).toBeNull();
    }
  });

  it("rejects invalid and reserved handles", () => {
    for (const h of ["ab", "-abc", "abc.", "a..b", "has space", "x".repeat(31)]) {
      expect(handleProblem(h)).toMatch(/Use 3/);
    }
    expect(handleProblem("login")).toMatch(/reserved/);
    expect(handleProblem("Edit")).toMatch(/reserved/);
    expect(handleProblem("icons")).toMatch(/reserved/);
    expect(handleProblem("handles")).toMatch(/reserved/);
  });
});

describe("urls", () => {
  it("allows only web and mail links", () => {
    expect(isSafeUrl("https://example.com")).toBe(true);
    expect(isSafeUrl("mailto:me@example.com")).toBe(true);
    expect(isSafeUrl("javascript:alert(1)")).toBe(false);
    expect(isSafeUrl("example.com")).toBe(false);
  });

  it("guesses icons from the host", () => {
    expect(guessIcon("https://www.tiktok.com/@x")).toBe("tiktok");
    expect(guessIcon("https://x.com/x")).toBe("x");
    expect(guessIcon("https://www.linkedin.com/in/x")).toBe("linkedin");
    expect(guessIcon("mailto:me@example.com")).toBe("email");
    expect(guessIcon("https://example.com")).toBe("link");
    expect(guessIcon("not a url")).toBe("link");
  });
});

describe("page helpers", () => {
  it("moves items within bounds", () => {
    expect(move([1, 2, 3], 0, 1)).toEqual([2, 1, 3]);
    expect(move([1, 2, 3], 0, -1)).toEqual([1, 2, 3]);
  });

  it("strips ids when converting a page to input", () => {
    const input = toInput({
      ...blankPage("abc"),
      avatar_url: null,
      updated_at: "",
      sections: [{ id: "s1", title: "A", links: [{ id: "l1", title: "T", url: "https://a.b/c", icon: "link" }] }],
    });
    expect(input.sections[0]).toEqual({
      title: "A",
      links: [{ title: "T", url: "https://a.b/c", icon: "link" }],
    });
  });
});

describe("import", () => {
  it("keeps the handle and replaces the rest", () => {
    const draft = { ...blankPage("me"), title: "Old" };
    const next = applyImport(draft, {
      source_url: "https://linktr.ee/x",
      title: "New",
      tagline: "Hi",
      socials: [{ icon: "github", url: "https://github.com/x" }],
      sections: [],
      avatar_data_url: null,
      warnings: [],
    });
    expect(next.handle).toBe("me");
    expect(next.title).toBe("New");
    expect(next.socials).toHaveLength(1);
    expect(next.sections).toEqual([{ title: "Links", links: [] }]);
  });

  it("turns a data URL into a file", async () => {
    const file = dataUrlToFile("data:image/png;base64,iVBORw0=");
    expect(file.type).toBe("image/png");
    expect(file.name).toBe("avatar.png");
    expect(new Uint8Array(await file.arrayBuffer()).slice(0, 4)).toEqual(
      new Uint8Array([0x89, 0x50, 0x4e, 0x47]),
    );
    expect(() => dataUrlToFile("https://x")).toThrow();
  });
});
