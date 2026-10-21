import axios from "axios";

const params = new URL(window.location.toString()).searchParams;
const backendAddr = params.get("server") ?? "[::1]:16880";

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
