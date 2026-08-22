import { useQuery } from "@tanstack/react-query";

import { get, post } from "./client";
import type { OrderCreateOut, OrderOut } from "./types";

// Отдельная функция-обёртка над window.location.assign, чтобы тесты могли её замокать.
export function redirect(url: string) {
  window.location.assign(url);
}

export async function createOrder(productIds: number[]) {
  return post<OrderCreateOut>("/orders", { product_ids: productIds });
}

export function useMyOrders() {
  return useQuery({ queryKey: ["orders", "my"], queryFn: () => get<OrderOut[]>("/orders/my") });
}

export function useOrder(
  orderId: number,
  opts?: { poll?: boolean; onPoll?: () => boolean },
) {
  return useQuery({
    queryKey: ["order", orderId],
    queryFn: () => get<OrderOut>(`/orders/${orderId}`),
    enabled: Number.isFinite(orderId) && orderId > 0,
    refetchInterval: opts?.poll
      ? (query) => {
          const status = query.state.data?.status;
          if (status === "delivered" || status === "failed") return false;
          // onPoll возвращает false, когда лимит попыток исчерпан
          if (opts.onPoll && !opts.onPoll()) return false;
          return 2000;
        }
      : undefined,
  });
}
