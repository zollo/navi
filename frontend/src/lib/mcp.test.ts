import { describe, expect, it } from "vitest";
import { base64Json, clientSetups, KEY_PLACEHOLDER, mcpUrl, urlWithKey } from "./mcp";

const URL_ = "https://navi.example.com/mcp";

describe("mcp setup", () => {
  it("builds the endpoint from the API origin", () => {
    expect(mcpUrl("", "https://navi.example.com")).toBe(URL_);
    expect(mcpUrl("http://localhost:8000/", "http://localhost:5173")).toBe(
      "http://localhost:8000/mcp",
    );
  });

  it("puts the key in the URL for URL-only clients", () => {
    expect(urlWithKey(URL_, "navi_a+b")).toBe(`${URL_}?key=navi_a%2Bb`);
  });

  it("uses a placeholder until a key is created", () => {
    const code = clientSetups(URL_, null).find((s) => s.id === "claude-code")!;
    expect(code.snippets[0].text).toBe(
      `claude mcp add --transport http navi ${URL_} --header "Authorization: Bearer ${KEY_PLACEHOLDER}"`,
    );
  });

  it("fills the key into every snippet and install link", () => {
    const setups = clientSetups(URL_, "navi_secret");
    for (const s of setups) {
      for (const snip of s.snippets) expect(snip.text).toContain("navi_secret");
      expect(JSON.stringify(s)).not.toContain(KEY_PLACEHOLDER);
    }
    const vscode = setups.find((s) => s.id === "vscode")!;
    const config = JSON.parse(
      decodeURIComponent(vscode.install!.href.slice("vscode:mcp/install?".length)),
    );
    expect(config).toEqual({
      name: "navi",
      type: "http",
      url: URL_,
      headers: { Authorization: "Bearer navi_secret" },
    });
    const cursor = setups.find((s) => s.id === "cursor")!;
    const encoded = new URL(cursor.install!.href).searchParams.get("config")!;
    expect(JSON.parse(atob(encoded))).toEqual({
      url: URL_,
      headers: { Authorization: "Bearer navi_secret" },
    });
    const mcpJson = JSON.parse(cursor.snippets[0].text);
    expect(mcpJson.mcpServers.navi.url).toBe(URL_);
  });

  it("base64-encodes non-ASCII safely", () => {
    expect(JSON.parse(new TextDecoder().decode(
      Uint8Array.from(atob(base64Json({ n: "Navi ✦" })), (c) => c.charCodeAt(0)),
    ))).toEqual({ n: "Navi ✦" });
  });
});
