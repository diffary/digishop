import { beforeEach, expect, test, vi } from "vitest";

import { ApiError, get, post } from "../api/client";
import { useAuthStore } from "../stores/auth";
import { jsonResponse } from "./test-utils";

beforeEach(() => {
  useAuthStore.setState({ token: null, email: null });
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn());
});

test("get вызывает fetch с базовым URL и парсит json", async () => {
  const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;
  mockFetch.mockResolvedValueOnce(jsonResponse(200, { id: 1, name: "Товар" }));

  const result = await get<{ id: number; name: string }>("/products");

  expect(mockFetch).toHaveBeenCalledWith(
    "http://localhost:8000/products",
    expect.objectContaining({ method: "GET" }),
  );
  expect(result).toEqual({ id: 1, name: "Товар" });
});

test("при наличии токена запрос содержит Authorization заголовок", async () => {
  useAuthStore.setState({ token: "abc123", email: "a@b.com" });
  const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;
  mockFetch.mockResolvedValueOnce(jsonResponse(200, {}));

  await get("/products");

  const callInit = mockFetch.mock.calls[0][1];
  expect(callInit.headers.Authorization).toBe("Bearer abc123");
});

test("не-2xx ответ с detail бросает ApiError со статусом и деталью", async () => {
  const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;
  mockFetch.mockResolvedValue(jsonResponse(400, { detail: "Bad request" }));

  await expect(post("/orders", {})).rejects.toMatchObject({
    status: 400,
    detail: "Bad request",
  });
  await expect(post("/orders", {})).rejects.toBeInstanceOf(ApiError);
});

test("401 ответ очищает токен в auth store", async () => {
  useAuthStore.setState({ token: "abc123", email: "a@b.com" });
  const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;
  mockFetch.mockResolvedValueOnce(jsonResponse(401, { detail: "Invalid credentials" }));

  await expect(get("/account")).rejects.toBeInstanceOf(ApiError);
  expect(useAuthStore.getState().token).toBeNull();
});
