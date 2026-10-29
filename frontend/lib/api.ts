// Every call to the FastAPI backend goes through this file.

const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) {
  throw new Error("NEXT_PUBLIC_API_URL is missing. Add it to frontend/.env.local");
}

// The access token lives only in memory (this variable), never in localStorage,
// so a malicious script on the page can't read it out of storage.
// After a page reload it's gone, and we get a new one with the refresh cookie.
let accessToken: string | null = null;

// Only one refresh may run at a time (see refreshSession below)
let refreshInFlight: Promise<boolean> | null = null;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type RequestOptions = {
  method?: "GET" | "POST";
  body?: unknown;
  auth?: boolean; // send the access token?
};

export async function api<T>(
  path: string,
  { method = "GET", body, auth = false }: RequestOptions = {},
): Promise<T> {
  let response = await send(path, method, body, auth);

  // Access token expired (they last 15 minutes)? Get a new one and try once more.
  if (response.status === 401 && auth && (await refreshSession())) {
    response = await send(path, method, body, auth);
  }

  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response));
  }
  if (response.status === 204) {
    return undefined as T; // e.g. logout sends no body
  }
  return (await response.json()) as T;
}

export function setAccessToken(token: string | null) {
  accessToken = token;
}

/**
 * Swap the refresh cookie for a new access token. Returns true if it worked.
 *
 * Two refreshes at the same moment would send the same cookie twice, which the
 * server treats as a stolen token and logs the user out. So parallel callers
 * share one request instead.
 */
export function refreshSession(): Promise<boolean> {
  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include", // send the HttpOnly refresh cookie
      });
      if (!response.ok) {
        accessToken = null;
        return false;
      }
      accessToken = (await response.json()).access_token;
      return true;
    } catch {
      accessToken = null;
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

/** A message we can show the user for any error. */
export function messageFrom(error: unknown): string {
  if (error instanceof TypeError) {
    // fetch() throws TypeError when the server can't be reached at all
    return "Can't reach the server. Is the backend running?";
  }
  if (error instanceof Error) {
    return error.message; // our ApiError, or a check like "Passwords don't match"
  }
  return "Something went wrong. Please try again.";
}

function send(path: string, method: string, body: unknown, auth: boolean) {
  const headers: Record<string, string> = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (auth && accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  return fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "include", // let the browser send/receive the refresh cookie
  });
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (Array.isArray(data.detail)) {
      // 422 validation errors: a list of problems
      return data.detail.map((problem: { msg: string }) => problem.msg).join(". ");
    }
  } catch {
    // the body wasn't JSON
  }
  return "Something went wrong. Please try again.";
}
