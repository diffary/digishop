import { beforeEach, expect, test } from "vitest";

import { useCartStore } from "../stores/cart";

beforeEach(() => {
  useCartStore.setState({ items: [] });
  localStorage.clear();
});

const item1 = { productId: 1, slug: "tank-pack", name: "Tank Pack 3D", price: 1999 };
const item2 = { productId: 2, slug: "sword-pack", name: "Sword Pack 3D", price: 999 };

test("add кладёт товар в items", () => {
  useCartStore.getState().add(item1);

  expect(useCartStore.getState().items).toEqual([item1]);
});

test("повторный add того же productId игнорируется", () => {
  useCartStore.getState().add(item1);
  useCartStore.getState().add({ ...item1, name: "другое имя", price: 1 });

  expect(useCartStore.getState().items).toEqual([item1]);
  expect(useCartStore.getState().items).toHaveLength(1);
});

test("remove удаляет товар по productId", () => {
  useCartStore.getState().add(item1);
  useCartStore.getState().add(item2);

  useCartStore.getState().remove(item1.productId);

  expect(useCartStore.getState().items).toEqual([item2]);
});

test("remove отсутствующего id — no-op", () => {
  useCartStore.getState().add(item1);

  useCartStore.getState().remove(999);

  expect(useCartStore.getState().items).toEqual([item1]);
});

test("clear очищает корзину", () => {
  useCartStore.getState().add(item1);
  useCartStore.getState().add(item2);

  useCartStore.getState().clear();

  expect(useCartStore.getState().items).toEqual([]);
});

test("total суммирует центы, count считает позиции", () => {
  useCartStore.getState().add(item1);
  useCartStore.getState().add(item2);

  const { items } = useCartStore.getState();
  expect(items.length).toBe(2);
  expect(items.reduce((sum, i) => sum + i.price, 0)).toBe(2998);
});

test("персист: после add localStorage содержит товар", () => {
  useCartStore.getState().add(item1);

  const raw = localStorage.getItem("digishop-cart");
  expect(raw).not.toBeNull();
  const parsed = JSON.parse(raw as string);
  expect(parsed.state.items).toEqual([item1]);
});
