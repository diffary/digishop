import { StrictMode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { QueryClient } from "@tanstack/react-query";
import { beforeEach, expect, test, vi } from "vitest";

import { AppRoutes } from "../App";
import { useAuthStore } from "../stores/auth";
import { jsonResponse, renderWithProviders } from "./test-utils";

beforeEach(() => {
  useAuthStore.setState({ token: null, email: null });
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn());
  vi.restoreAllMocks();
});

function renderStrict(initialEntries: string[]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>
          <AppRoutes />
        </MemoryRouter>
      </QueryClientProvider>
    </StrictMode>,
  );
}

test("успешный обмен кода кладёт токен и email, редиректит в каталог", async () => {
  const fetchMock = vi.fn().mockImplementation((url: string) => {
    if (String(url).includes("/auth/exchange")) {
      return Promise.resolve(jsonResponse(200, { access_token: "tok-1", token_type: "bearer" }));
    }
    if (String(url).includes("/auth/me")) {
      return Promise.resolve(jsonResponse(200, { id: 1, email: "user@example.com" }));
    }
    return Promise.resolve(jsonResponse(200, []));
  });
  vi.stubGlobal("fetch", fetchMock);

  renderWithProviders(<AppRoutes />, { initialEntries: ["/auth/callback?code=abc"] });

  await waitFor(() => {
    expect(useAuthStore.getState().token).toBe("tok-1");
    expect(useAuthStore.getState().email).toBe("user@example.com");
  });

  const exchangeCalls = fetchMock.mock.calls.filter((call) =>
    String(call[0]).includes("/auth/exchange"),
  );
  expect(exchangeCalls).toHaveLength(1);
  const [, exchangeInit] = exchangeCalls[0];
  expect(JSON.parse(exchangeInit.body)).toEqual({ code: "abc" });
});

test("StrictMode двойной монтаж делает ровно один запрос обмена", async () => {
  const fetchMock = vi.fn().mockImplementation((url: string) => {
    if (String(url).includes("/auth/exchange")) {
      return Promise.resolve(jsonResponse(200, { access_token: "tok-2", token_type: "bearer" }));
    }
    if (String(url).includes("/auth/me")) {
      return Promise.resolve(jsonResponse(200, { id: 2, email: "user2@example.com" }));
    }
    return Promise.resolve(jsonResponse(200, []));
  });
  vi.stubGlobal("fetch", fetchMock);

  renderStrict(["/auth/callback?code=abc"]);

  await waitFor(() => {
    expect(useAuthStore.getState().token).toBe("tok-2");
  });

  const exchangeCalls = fetchMock.mock.calls.filter((call) =>
    String(call[0]).includes("/auth/exchange"),
  );
  expect(exchangeCalls).toHaveLength(1);
});

test("невалидный/просроченный код показывает ошибку и не логинит", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(jsonResponse(400, { detail: "Invalid or expired code" })),
  );

  renderWithProviders(<AppRoutes />, { initialEntries: ["/auth/callback?code=bad"] });

  await waitFor(() => {
    expect(screen.getByText("Не удалось войти через Google")).toBeInTheDocument();
  });
  expect(screen.getByRole("link", { name: "Попробовать ещё раз" })).toHaveAttribute(
    "href",
    "/login",
  );
  expect(useAuthStore.getState().token).toBeNull();
});

test("без параметра code сразу показывает ошибку без запроса", async () => {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);

  renderWithProviders(<AppRoutes />, { initialEntries: ["/auth/callback"] });

  await waitFor(() => {
    expect(screen.getByText("Не удалось войти через Google")).toBeInTheDocument();
  });
  expect(fetchMock).not.toHaveBeenCalled();
});
