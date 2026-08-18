import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { AppRoutes } from "../App";
import { jsonResponse, renderWithProviders } from "./test-utils";

const products = [
  {
    id: 1,
    name: "Tank Pack 3D",
    slug: "tank-pack-3d",
    description: "Набор танков в 3D",
    price: 1999,
    image_url: null,
    category_slug: "models",
  },
];

const categories = [{ id: 1, name: "Модели", slug: "models" }];

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

function mockCatalogFetch(productsResponse: unknown = products, status = 200) {
  const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;
  mockFetch.mockImplementation((url: string) => {
    if (url.includes("/categories")) {
      return Promise.resolve(jsonResponse(200, categories));
    }
    if (url.includes("/products")) {
      return Promise.resolve(jsonResponse(status, productsResponse));
    }
    return Promise.resolve(jsonResponse(200, {}));
  });
  return mockFetch;
}

test("каталог рендерит карточки товаров из мока", async () => {
  mockCatalogFetch();

  renderWithProviders(<AppRoutes />, { initialEntries: ["/"] });

  expect(await screen.findByText("Tank Pack 3D")).toBeInTheDocument();
  expect(screen.getByText("$19.99")).toBeInTheDocument();
});

test("смена категории вызывает fetch с параметром category", async () => {
  const mockFetch = mockCatalogFetch();

  renderWithProviders(<AppRoutes />, { initialEntries: ["/"] });

  await screen.findByText("Tank Pack 3D");

  fireEvent.change(screen.getByRole("combobox"), { target: { value: "models" } });

  await waitFor(() => {
    expect(
      mockFetch.mock.calls.some((call) => String(call[0]).includes("category=models")),
    ).toBe(true);
  });
});

test("поиск с дебаунсом вызывает fetch с параметром search", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  try {
    const mockFetch = mockCatalogFetch();

    renderWithProviders(<AppRoutes />, { initialEntries: ["/"] });

    await vi.waitFor(() => screen.getByText("Tank Pack 3D"));

    fireEvent.change(screen.getByPlaceholderText("Поиск..."), { target: { value: "tank" } });

    await vi.advanceTimersByTimeAsync(350);

    await vi.waitFor(() => {
      if (
        !mockFetch.mock.calls.some((call) => String(call[0]).includes("search=tank"))
      ) {
        throw new Error("not called yet");
      }
    });
  } finally {
    vi.useRealTimers();
  }
});

test("пустой список товаров показывает сообщение", async () => {
  mockCatalogFetch([]);

  renderWithProviders(<AppRoutes />, { initialEntries: ["/"] });

  expect(await screen.findByText("Ничего не найдено")).toBeInTheDocument();
});

test("ошибка сервера показывает сообщение об ошибке", async () => {
  mockCatalogFetch({ detail: "Server error" }, 500);

  renderWithProviders(<AppRoutes />, { initialEntries: ["/"] });

  expect(await screen.findByText("Не удалось загрузить каталог")).toBeInTheDocument();
});

test("страница товара рендерит данные из мока", async () => {
  const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;
  mockFetch.mockImplementation((url: string) => {
    if (url.includes("/products/tank-pack-3d")) {
      return Promise.resolve(jsonResponse(200, products[0]));
    }
    return Promise.resolve(jsonResponse(200, {}));
  });

  renderWithProviders(<AppRoutes />, { initialEntries: ["/product/tank-pack-3d"] });

  expect(await screen.findByText("Tank Pack 3D")).toBeInTheDocument();
  expect(screen.getByText("Набор танков в 3D")).toBeInTheDocument();
  expect(screen.getByText("$19.99")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "В корзину" })).toBeInTheDocument();
});

test("404 на странице товара показывает «Товар не найден»", async () => {
  const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;
  mockFetch.mockImplementation(() =>
    Promise.resolve(jsonResponse(404, { detail: "Product not found" })),
  );

  renderWithProviders(<AppRoutes />, { initialEntries: ["/product/unknown"] });

  expect(await screen.findByText("Товар не найден")).toBeInTheDocument();
});
