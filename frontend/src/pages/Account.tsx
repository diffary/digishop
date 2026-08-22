import { Link } from "react-router";

import { API_URL } from "../api/client";
import { useMyOrders } from "../api/orders";
import type { OrderOut } from "../api/types";
import { formatPrice } from "../lib/format";

const STATUS_LABELS: Record<OrderOut["status"], string> = {
  pending: "Ожидает оплаты",
  paid: "Оплачен",
  delivered: "Доставлен",
  failed: "Ошибка оплаты",
};

const STATUS_CLASSES: Record<OrderOut["status"], string> = {
  pending: "bg-gray-100 text-gray-700",
  paid: "bg-blue-100 text-blue-700",
  delivered: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

function StatusBadge({ status }: { status: OrderOut["status"] }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  );
}

function OrderCard({ order }: { order: OrderOut }) {
  return (
    <li className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-medium">Заказ №{order.id}</span>
          <StatusBadge status={order.status} />
        </div>
        <span className="text-indigo-600 font-medium">{formatPrice(order.total)}</span>
      </div>
      <p className="text-sm text-gray-500 mt-1">
        {new Date(order.created_at).toLocaleDateString("ru")}
      </p>
      {order.status === "delivered" && (
        <ul className="mt-3 divide-y divide-gray-200 border-y border-gray-200">
          {order.items.map((item) => (
            <li key={item.product_id} className="flex items-center justify-between py-2">
              <span>{item.product_name}</span>
              {item.download_token ? (
                <a
                  href={`${API_URL}/downloads/${item.download_token}`}
                  className="text-indigo-600 hover:underline font-medium"
                >
                  Скачать
                </a>
              ) : (
                <span className="text-gray-400">ссылка истекла</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export default function Account() {
  const { data: orders, isLoading, error } = useMyOrders();

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Кабинет</h1>
      {isLoading && <p className="text-gray-500">Загрузка...</p>}
      {error && <p className="text-red-600">Не удалось загрузить заказы</p>}
      {orders && orders.length === 0 && (
        <div>
          <p className="text-lg mb-4">Заказов пока нет</p>
          <Link to="/" className="text-indigo-600 hover:underline">
            В каталог
          </Link>
        </div>
      )}
      {orders && orders.length > 0 && (
        <ul className="flex flex-col gap-4">
          {orders.map((order) => (
            <OrderCard key={order.id} order={order} />
          ))}
        </ul>
      )}
    </div>
  );
}
