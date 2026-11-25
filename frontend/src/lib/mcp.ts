// Setup snippets for connecting AI assistants to Navi's MCP server (/mcp).

export const KEY_PLACEHOLDER = "<your API key>";
export const SERVER_NAME = "navi";

export type ClientId = "claude-code" | "claude-app" | "vscode" | "cursor" | "other";

export interface Snippet {
  label: string;
  language: "shell" | "json" | "text";
  text: string;
}

export interface ClientSetup {
  id: ClientId;
  name: string;
  steps: string[];
  snippets: Snippet[];
  // A link that installs the server in one click, where the client supports one.
  install?: { label: string; href: string };
  note?: string;
}

// The MCP endpoint for an API origin ("" means this page's own origin).
export function mcpUrl(apiBase: string, origin: string): string {
  return `${(apiBase || origin).replace(/\/$/, "")}/mcp`;
}

// For clients that take only a URL. The key is part of the URL, so it's a secret.
export function urlWithKey(url: string, key: string): string {
  return `${url}?key=${encodeURIComponent(key)}`;
}

function json(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

// UTF-8 safe base64 (Cursor's install link carries the config this way).
export function base64Json(value: unknown): string {
  const bytes = new TextEncoder().encode(JSON.stringify(value));
  let bin = "";
  bytes.forEach((b) => (bin += String.fromCharCode(b)));
  return btoa(bin);
}

export function clientSetups(url: string, key: string | null): ClientSetup[] {
  const k = key ?? KEY_PLACEHOLDER;
  const auth = `Bearer ${k}`;
  const httpServer = { url, headers: { Authorization: auth } };

  const vscodeServer = { type: "http", ...httpServer };
  const vscodeInstall = { name: SERVER_NAME, ...vscodeServer };

  return [
    {
      id: "claude-code",
      name: "Claude Code",
      steps: ["Run this in a terminal. Add --scope user to use Navi in every project."],
      snippets: [
        {
          label: "Terminal",
          language: "shell",
          text: `claude mcp add --transport http ${SERVER_NAME} ${url} --header "Authorization: ${auth}"`,
        },
      ],
    },
    {
      id: "claude-app",
      name: "Claude app",
      steps: [
        "On claude.ai or in the Claude desktop app, open Settings → Connectors and choose “Add custom connector”.",
        "Name it Navi and paste the URL below (it includes your key, so keep it private).",
        "Turn the connector on in a chat from the tools menu, then ask Claude to update your page.",
      ],
      snippets: [{ label: "Connector URL", language: "text", text: urlWithKey(url, k) }],
      note: "Claude connects from the internet, so this only works when Navi is reachable from outside your network.",
    },
    {
      id: "vscode",
      name: "VS Code · Copilot",
      steps: [
        "Click Install in VS Code (or add the snippet to .vscode/mcp.json, or to your user mcp.json via “MCP: Open User Configuration”).",
        "In Copilot Chat, switch to Agent mode and enable the Navi tools.",
      ],
      install: {
        label: "Install in VS Code",
        href: `vscode:mcp/install?${encodeURIComponent(JSON.stringify(vscodeInstall))}`,
      },
      snippets: [
        { label: "mcp.json", language: "json", text: json({ servers: { [SERVER_NAME]: vscodeServer } }) },
      ],
    },
    {
      id: "cursor",
      name: "Cursor",
      steps: [
        "Click Install in Cursor, or add the snippet to ~/.cursor/mcp.json (or .cursor/mcp.json in a project).",
      ],
      install: {
        label: "Install in Cursor",
        href: `cursor://anysphere.cursor-deeplink/mcp/install?name=${SERVER_NAME}&config=${encodeURIComponent(base64Json(httpServer))}`,
      },
      snippets: [
        { label: "mcp.json", language: "json", text: json({ mcpServers: { [SERVER_NAME]: httpServer } }) },
      ],
    },
    {
      id: "other",
      name: "Other",
      steps: [
        "Navi speaks MCP over streamable HTTP. Most clients (Windsurf, Zed, Copilot in JetBrains, ChatGPT developer mode…) accept one of these.",
        "Clients that only run local servers can bridge with mcp-remote.",
      ],
      snippets: [
        { label: "URL + header", language: "json", text: json({ mcpServers: { [SERVER_NAME]: { type: "http", ...httpServer } } }) },
        { label: "URL only", language: "text", text: urlWithKey(url, k) },
        {
          label: "Local bridge (mcp-remote)",
          language: "json",
          text: json({
            mcpServers: {
              [SERVER_NAME]: {
                command: "npx",
                args: ["-y", "mcp-remote", url, "--header", "Authorization:${NAVI_AUTH}"],
                env: { NAVI_AUTH: auth },
              },
            },
          }),
        },
      ],
    },
  ];
}
