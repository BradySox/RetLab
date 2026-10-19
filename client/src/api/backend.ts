import axios from "axios";

const PHONE_LINK = "retlab.phoneLink";

// A home-screen icon opens the manifest's start_url, which carries no query, so
// the phone keeps the link it was first opened with (§115).
function linkParams(): URLSearchParams {
  const params = new URL(window.location.toString()).searchParams;
  try {
    if (params.get("view") === "phone" && params.get("key")) {
      window.localStorage.setItem(PHONE_LINK, params.toString());
    } else if (!params.get("key") && window.location.protocol.startsWith("http")) {
      const saved = window.localStorage.getItem(PHONE_LINK);
      if (saved) {
        return new URLSearchParams(saved);
      }
    }
  } catch {
    // Storage can be off (private browsing); the link in the address bar still works.
  }
  return params;
}

const params = linkParams();
const backendAddr = params.get("server") ?? "[::1]:16880";

// The phone map's link (§115) asks for the read-only view; the server refuses
// the phone's writes anyway, so this only keeps the page from offering them.
export const READ_ONLY = params.get("view") === "phone";

// The server refuses a request without this key. Qt passes it beside `server`.
export const API_KEY = params.get("key") ?? "";
export const API_KEY_HEADERS: Record<string, string> = API_KEY
  ? { "X-API-Key": API_KEY }
  : {};

// For requests that cannot carry a header: map tiles, the websocket, plain fetch.
export function withToken(url: string): string {
  if (!API_KEY) {
    return url;
  }
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}token=${encodeURIComponent(API_KEY)}`;
}

export const HTTP_URL = `http://${backendAddr}/`;

export const backend = axios.create({
  baseURL: HTTP_URL,
  headers: API_KEY_HEADERS,
});

export const WEBSOCKET_URL = withToken(`ws://${backendAddr}/eventstream`);

export default backend;
