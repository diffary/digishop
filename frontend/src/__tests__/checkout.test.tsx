import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { AppRoutes } from "../App";
import { API_URL } from "../api/client";
import * as ordersApi from "../api/orders";
import { useAuthStore } from "../stores/auth";
import { useCartStore } from "../stores/cart";
import { jsonResponse, renderWithProviders } from "./test-utils";

const item1 = { productId: 1, slug: "tank-pack", name: "Tank Pack 3D", price: 1999 };

beforeEach(() => {
  useCartStore.setState({ items: [] });
  useAuthStore.setState({ token: null, email: null });
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn());
  vi.restoreAllMocks();
});

test("оформить заказ без авторизации отправляет на /login", async () => {
  useCartStore.setState({ items: [item1] });

  renderWithProviders(<AppRoutes />, { initialEntries: ["/cart"] });

  fireEvent.click(screen.getByRole("button", { name: "Оформить заказ" }));

  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });
});

test("оформить заказ авторизованным юзером создаёт заказ, чистит корзину и редиректит на checkout_url", async () => {
  useAuthStore.setState({ token: "tok123", email: "user@example.com" });
  useCartStore.setState({ items: [item1] });

  const redirectSpy = vi.spyOn(ordersApi, "redirect").mockImplementation(() => {});

  const mockFetch = vi.fn().mockResolvedValue(
    jsonResponse(201, { order_id: 5, checkout_url: "https://stripe.test/checkout/5" }),
  );
  vi.stubGlobal("fetch", mockFetch);

  renderWithProviders(<AppRoutes />, { initialEntries: ["/cart"] });

  fireEvent.click(screen.getByRole("button", { name: "Оформить заказ" }));

  await waitFor(() => {
    expect(redirectSpy).toHaveBeenCalledWith("https://stripe.test/checkout/5");
  });

  expect(useCartStore.getState().items).toEqual([]);

  const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.find((c) =>
    String(c[0]).includes("/orders"),
  );
  expect(call).toBeTruthy();
  expect(JSON.parse(call![1].body)).toEqual({ product_ids: [1] });
});

test("OrderSuccess: pending показывает ожидание подтверждения оплаты", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      jsonResponse(200, {
        id: 1,
        status: "pending",
        total: 1999,
        created_at: "2026-08-19T00:00:00Z",
        items: [],
      }),
    ),
  );

  renderWithProviders(<AppRoutes />, { initialEntries: ["/order/success?order_id=1"] });

  expect(await screen.findByText("Ждём подтверждение оплаты…")).toBeInTheDocument();
});

test("OrderSuccess: paid показывает подготовку файлов", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      jsonResponse(200, {
        id: 1,
        status: "paid",
        total: 1999,
        created_at: "2026-08-19T00:00:00Z",
        items: [],
      }),
    ),
  );

  renderWithProviders(<AppRoutes />, { initialEntries: ["/order/success?order_id=1"] });

  expect(await screen.findByText("Оплачено, готовим файлы…")).toBeInTheDocument();
});

test("OrderSuccess: delivered показывает готово и ссылки скачивания", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      jsonResponse(200, {
        id: 1,
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
        ],
      }),
    ),
  );

  renderWithProviders(<AppRoutes />, { initialEntries: ["/order/success?order_id=1"] });

  expect(await screen.findByText("Готово!")).toBeInTheDocument();
  const link = screen.getByRole("link", { name: "Скачать" });
  expect(link).toHaveAttribute("href", `${API_URL}/downloads/tok-abc`);
});

test("OrderSuccess: delivered с истёкшей ссылкой не показывает ссылку", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      jsonResponse(200, {
        id: 1,
        status: "delivered",
        total: 1999,
        created_at: "2026-08-19T00:00:00Z",
        items: [
          {
            product_id: 1,
            price_at_purchase: 1999,
            product_name: "Tank Pack 3D",
            download_token: null,
          },
        ],
      }),
    ),
  );

  renderWithProviders(<AppRoutes />, { initialEntries: ["/order/success?order_id=1"] });

  expect(await screen.findByText("Готово!")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Скачать" })).not.toBeInTheDocument();
  expect(screen.getByText(/ссылка истекла/)).toBeInTheDocument();
});

test("OrderSuccess: failed показывает ошибку оплаты и ссылку в каталог", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      jsonResponse(200, {
        id: 1,
        status: "failed",
        total: 1999,
        created_at: "2026-08-19T00:00:00Z",
        items: [],
      }),
    ),
  );

  renderWithProviders(<AppRoutes />, { initialEntries: ["/order/success?order_id=1"] });

  expect(await screen.findByText("Оплата не прошла")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "В каталог" })).toBeInTheDocument();
});

test("OrderSuccess: после 60 секунд pending показывает «загляните позже»", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  try {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(200, {
          id: 1,
          status: "pending",
          total: 1999,
          created_at: "2026-08-19T00:00:00Z",
          items: [],
        }),
      ),
    );

    renderWithProviders(<AppRoutes />, { initialEntries: ["/order/success?order_id=1"] });
    expect(await screen.findByText("Ждём подтверждение оплаты…")).toBeInTheDocument();

    // прыгаем за бюджет ожидания и даём интервалу поллинга сработать
    await vi.advanceTimersByTimeAsync(61_000);

    expect(await screen.findByText(/загляните в/)).toBeInTheDocument();
    expect(screen.queryByText("Ждём подтверждение оплаты…")).not.toBeInTheDocument();
  } finally {
    vi.useRealTimers();
  }
});

test("OrderCancel рендерит текст отмены и ссылку в кабинет", () => {
  renderWithProviders(<AppRoutes />, { initialEntries: ["/order/cancel"] });

  expect(screen.getByText("Оплата отменена")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "В кабинет" })).toBeInTheDocument();
});
