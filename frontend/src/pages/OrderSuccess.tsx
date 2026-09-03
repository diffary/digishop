import { useRef, useState } from "react";
import { Link, useSearchParams } from "react-router";

import { API_URL } from "../api/client";
import { useOrder } from "../api/orders";

// Лимит ожидания в мс: дальше отправляем юзера в кабинет.
// Именно время, а не счётчик вызовов: refetchInterval-колбэк TanStack
// дёргается чаще, чем реально уходят запросы (mount, оба апдейта цикла).
const POLL_BUDGET_MS = 60_000;

export default function OrderSuccess() {
  const [searchParams] = useSearchParams();
  const orderId = Number(searchParams.get("order_id"));
  // capped — React-state, а не ref: остановка поллинга сама по себе
  // не перерисовывает компонент (payload не меняется — structural sharing
  // не уведомляет подписчиков), поэтому смену сообщения форсируем setState'ом.
  const [capped, setCapped] = useState(false);
  const startedAt = useRef(Date.now());
  const { data: order, isLoading, error } = useOrder(orderId, {
    poll: !capped,
    onPoll: () => {
      if (Date.now() - startedAt.current > POLL_BUDGET_MS) {
        setCapped(true);
        return false;
      }
      return true;
    },
  });

  if (!Number.isFinite(orderId) || orderId <= 0) {
    return (
      <div>
        <p className="text-lg mb-4">Заказ не найден</p>
        <Link to="/" className="text-indigo-600 hover:underline">
          В каталог
        </Link>
      </div>
    );
  }

  if (isLoading) return <p className="text-gray-500">Загрузка...</p>;
  if (error || !order) return <p className="text-red-600">Не удалось загрузить заказ</p>;

  if (order.status === "failed") {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-4">Оплата не прошла</h1>
        <Link to="/" className="text-indigo-600 hover:underline">
          В каталог
        </Link>
      </div>
    );
  }

  if (order.status === "pending" || order.status === "paid") {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-4">Заказ №{order.id}</h1>
        {capped ? (
          <p className="text-gray-700">
            Оплата ещё обрабатывается — загляните в{" "}
            <Link to="/account" className="text-indigo-600 hover:underline">
              кабинет
            </Link>{" "}
            чуть позже.
          </p>
        ) : (
          <p className="text-gray-700 animate-pulse">
            {order.status === "pending" ? "Ждём подтверждение оплаты…" : "Оплачено, готовим файлы…"}
          </p>
        )}
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Готово!</h1>
      <ul className="divide-y divide-gray-200 border-y border-gray-200">
        {order.items.map((item) => (
          <li key={item.product_id} className="flex items-center justify-between py-3">
            <span>{item.product_name}</span>
            {item.download_token ? (
              <a
                href={`${API_URL}/downloads/${item.download_token}`}
                className="text-indigo-600 hover:underline font-medium"
              >
                Скачать
              </a>
            ) : (
              <span className="text-gray-400">ссылка истекла — обновите в кабинете</span>
            )}
          </li>
        ))}
      </ul>
      <p className="mt-6">
        <Link to="/account" className="text-indigo-600 hover:underline">
          В кабинет
        </Link>
      </p>
    </div>
  );
}
