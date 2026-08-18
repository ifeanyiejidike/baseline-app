/**
 * Thin fetch wrapper for the Baseline API.
 *
 * Deliberately NOT a full data-fetching library (no react-query/SWR here —
 * package.json doesn't include one, so this stays framework-agnostic
 * until/unless that's added). Handles the two headers every authenticated
 * Baseline endpoint needs — `Authorization: Bearer <token>` and
 * `X-Organization-Id: <org uuid>` — and normalizes error responses into a
 * typed `ApiError` instead of every call site re-parsing `response.json()`
 * on failure.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  code?: string;
  errorId?: string;

  constructor(message: string, status: number, code?: string, errorId?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.errorId = errorId;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  accessToken?: string | null;
  organizationId?: string | null;
  /** Set true for multipart/form-data uploads — skips JSON.stringify and
   * the Content-Type header (the browser sets the multipart boundary). */
  isFormData?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, accessToken, organizationId, isFormData, headers, ...rest } = options;

  const finalHeaders: HeadersInit = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    ...(organizationId ? { "X-Organization-Id": organizationId } : {}),
    ...headers,
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: finalHeaders,
    body: body === undefined ? undefined : isFormData ? (body as FormData) : JSON.stringify(body),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const detail =
      isJson && typeof data === "object" && data !== null && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : `Request failed with status ${response.status}`;
    const code = isJson && typeof data === "object" && data !== null && "code" in data
      ? String((data as { code: unknown }).code)
      : undefined;
    const errorId = isJson && typeof data === "object" && data !== null && "error_id" in data
      ? String((data as { error_id: unknown }).error_id)
      : undefined;
    throw new ApiError(detail, response.status, code, errorId);
  }

  return data as T;
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PATCH", body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PUT", body }),
  delete: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: "DELETE" }),
};
