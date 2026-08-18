import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface CartItem {
  productId: number;
  slug: string;
  name: string;
  price: number;
}

interface CartState {
  items: CartItem[];
  add: (item: CartItem) => void;
  remove: (productId: number) => void;
  clear: () => void;
}

export const useCartStore = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      add: (item) =>
        set((state) =>
          state.items.some((i) => i.productId === item.productId)
            ? state
            : { items: [...state.items, item] },
        ),
      remove: (productId) =>
        set((state) => ({ items: state.items.filter((i) => i.productId !== productId) })),
      clear: () => set({ items: [] }),
    }),
    { name: "digishop-cart" },
  ),
);

export const useCartCount = () => useCartStore((state) => state.items.length);

export const useCartTotal = () =>
  useCartStore((state) => state.items.reduce((sum, item) => sum + item.price, 0));
