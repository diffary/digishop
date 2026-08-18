import { screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { AppRoutes } from "../App";
import { renderWithProviders } from "./test-utils";

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "Error",
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response;
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;
  mockFetch.mockImplementation((url: string) => {
    if (url.includes("/categories")) return Promise.resolve(jsonResponse(200, []));
    if (url.includes("/products")) return Promise.resolve(jsonResponse(200, []));
    return Promise.resolve(jsonResponse(200, {}));
  });
});

test("шапка показывает навигацию", () => {
  renderWithProviders(<AppRoutes />, { initialEntries: ["/"] });
  expect(screen.getByRole("link", { name: "Каталог" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Корзина/ })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Войти" })).toBeInTheDocument();
});

test("страница каталога рендерится на корне", () => {
  renderWithProviders(<AppRoutes />, { initialEntries: ["/"] });
  expect(screen.getByRole("heading", { name: "Каталог" })).toBeInTheDocument();
});
