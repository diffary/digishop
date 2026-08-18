import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface CartItem {
  productId: number;
  slug: string;
  name: string;
  price: number; // центы, как везде в проекте
}

interface CartState {
  items: CartItem[];
  add: (item: CartItem) => void;
  remove: (productId: number) => void;
  clear: () => void;
}

// ТВОЁ УПРАЖНЕНИЕ №4: реализуй стор.
// Контракт: add игнорирует дубль по productId (первый победил);
// remove убирает по productId; clear очищает.
// Помни про иммутабельность: НЕ push, а новый массив.
// persist уже подключён — ключ localStorage менять нельзя, тесты его проверяют.
export const useCartStore = create<CartState>()(
  persist(
    (set) => ({
      
      items: [],
      add: (item) => {
        set((state) => {
          if (!state.items.some((i) => i.productId === item.productId)) {
            return { items: [...state.items, item] };
          }
          return state; // если дубль, возвращаем текущее состояние без изменений
        });
      },
      remove: (productId) => {
        set((state) => ({
          items: state.items.filter((item) => item.productId !== productId),
        }));
      },
      clear: () => {
        set({ items: [] });
      },
    }),
    { name: "digishop-cart" },
  ),
);

// Селекторы-хуки: count — число позиций, total — сумма цен в центах.
export function useCartCount(): number {
    return useCartStore((state) => state.items.length);
}

export function useCartTotal(): number {
    return useCartStore((state) =>
      state.items.reduce((total, item) => total + item.price, 0),
    );
}
