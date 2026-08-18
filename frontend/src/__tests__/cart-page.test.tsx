import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";

import { AppRoutes } from "../App";
import { useCartStore } from "../stores/cart";
import { renderWithProviders } from "./test-utils";

const item1 = { productId: 1, slug: "tank-pack", name: "Tank Pack 3D", price: 1999 };
const item2 = { productId: 2, slug: "sword-pack", name: "Sword Pack 3D", price: 999 };

beforeEach(() => {
  useCartStore.setState({ items: [] });
  localStorage.clear();
});

test("корзина с товарами показывает названия, цены и итого", () => {
  useCartStore.setState({ items: [item1, item2] });

  renderWithProviders(<AppRoutes />, { initialEntries: ["/cart"] });

  expect(screen.getByText("Tank Pack 3D")).toBeInTheDocument();
  expect(screen.getByText("Sword Pack 3D")).toBeInTheDocument();
  expect(screen.getByText("$19.99")).toBeInTheDocument();
  expect(screen.getByText("$9.99")).toBeInTheDocument();
  expect(screen.getByText("Итого: $29.98")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Оформить заказ" })).toBeInTheDocument();
});

test("кнопка удаления убирает позицию из корзины", () => {
  useCartStore.setState({ items: [item1, item2] });

  renderWithProviders(<AppRoutes />, { initialEntries: ["/cart"] });

  fireEvent.click(screen.getByLabelText("Удалить Tank Pack 3D"));

  expect(screen.queryByText("Tank Pack 3D")).not.toBeInTheDocument();
  expect(screen.getByText("Sword Pack 3D")).toBeInTheDocument();
});

test("пустая корзина показывает сообщение и ссылку в каталог", () => {
  renderWithProviders(<AppRoutes />, { initialEntries: ["/cart"] });

  expect(screen.getByText("Корзина пуста")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "В каталог" })).toBeInTheDocument();
});

test("счётчик в шапке отражает количество товаров в корзине", () => {
  useCartStore.setState({ items: [item1, item2] });

  renderWithProviders(<AppRoutes />, { initialEntries: ["/cart"] });

  expect(screen.getByText("2")).toBeInTheDocument();
});
