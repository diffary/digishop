import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { AppRoutes } from "../App";
import { API_URL } from "../api/client";
import { useAuthStore } from "../stores/auth";
import { useCartStore } from "../stores/cart";
import { jsonResponse, renderWithProviders } from "./test-utils";

beforeEach(() => {
  useCartStore.setState({ items: [] });
  useAuthStore.setState({ token: null, email: null });
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn());
  vi.restoreAllMocks();
});

test("/account без токена редиректит на /login", async () => {
  renderWithProviders(<AppRoutes />, { initialEntries: ["/account"] });

  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });
});

test("после логина с /account редиректит обратно в кабинет", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) => {
      if (String(url).includes("/auth/login")) {
        return Promise.resolve(jsonResponse(200, { access_token: "tok", token_type: "bearer" }));
      }
      if (String(url).includes("/orders/my")) {
        return Promise.resolve(jsonResponse(200, []));
      }
      return Promise.resolve(jsonResponse(200, {}));
    }),
  );

  renderWithProviders(<AppRoutes />, { initialEntries: ["/account"] });

  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });

  fireEvent.change(screen.getByLabelText("Email"), { target: { value: "user@example.com" } });
  fireEvent.change(screen.getByLabelText("Пароль"), { target: { value: "password123" } });
  fireEvent.click(screen.getByRole("button", { name: "Войти" }));

  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "Кабинет" })).toBeInTheDocument();
  });
});

test("/account с токеном показывает список заказов", async () => {
  useAuthStore.setState({ token: "tok123", email: "user@example.com" });
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      jsonResponse(200, [
        {
          id: 5,
          status: "paid",
          total: 1999,
          created_at: "2026-08-19T00:00:00Z",
          items: [],
        },
      ]),
    ),
  );

  renderWithProviders(<AppRoutes />, { initialEntries: ["/account"] });

  expect(await screen.findByText("Заказ №5")).toBeInTheDocument();
  expect(screen.getByText("Оплачен")).toBeInTheDocument();
  expect(screen.getByText("$19.99")).toBeInTheDocument();
});

test("delivered-заказ показывает items с ссылками на скачивание", async () => {
  useAuthStore.setState({ token: "tok123", email: "user@example.com" });
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      jsonResponse(200, [
        {
          id: 7,
          status: "delivered",
          total: 1999,
          created_at: "2026-08-19T00:00:00Z",
          items: [
            {
              product_id: 1,
              price_at_purchase: 1999,
              product_name: "Tank Pack 3D",
              download_token: "tok-abc",
            },
            {
              product_id: 2,
              price_at_purchase: 500,
              product_name: "Другой товар",
              download_token: null,
            },
          ],
        },
      ]),
    ),
  );

  renderWithProviders(<AppRoutes />, { initialEntries: ["/account"] });

  expect(await screen.findByText("Заказ №7")).toBeInTheDocument();
  expect(screen.getByText("Доставлен")).toBeInTheDocument();
  const link = screen.getByRole("link", { name: "Скачать" });
  expect(link).toHaveAttribute("href", `${API_URL}/downloads/tok-abc`);
  expect(screen.getByText(/ссылка истекла/)).toBeInTheDocument();
});

test("пустой список заказов показывает приглашение в каталог", async () => {
  useAuthStore.setState({ token: "tok123", email: "user@example.com" });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, [])));

  renderWithProviders(<AppRoutes />, { initialEntries: ["/account"] });

  expect(await screen.findByText("Заказов пока нет")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "В каталог" })).toBeInTheDocument();
});

test("401 при загрузке заказов очищает авторизацию и предлагает войти", async () => {
  useAuthStore.setState({ token: "expired-tok", email: "user@example.com" });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(401, { detail: "Unauthorized" })));

  renderWithProviders(<AppRoutes />, { initialEntries: ["/account"] });

  await waitFor(() => {
    expect(useAuthStore.getState().token).toBeNull();
  });
});
