import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { ApiError } from "../api/client";
import { createOrder, redirect } from "../api/orders";
import { formatPrice } from "../lib/format";
import { useIsAuthed } from "../stores/auth";
import { useCartStore, useCartTotal } from "../stores/cart";

export default function Cart() {
  const items = useCartStore((state) => state.items);
  const remove = useCartStore((state) => state.remove);
  const clear = useCartStore((state) => state.clear);
  const total = useCartTotal();
  const isAuthed = useIsAuthed();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCheckout() {
    if (!isAuthed) {
      navigate("/login", { state: { from: "/cart" } });
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await createOrder(items.map((i) => i.productId));
      // Корзину чистим сразу после создания заказа, ещё до ухода на Stripe:
      // заказ уже существует, при отмене он виден в кабинете как pending
      // и протухнет через 75 минут (beat-задача на бэкенде).
      clear();
      redirect(res.checkout_url);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Не удалось создать заказ");
      setLoading(false);
    }
  }

  if (items.length === 0) {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-4">Корзина</h1>
        <p className="text-lg mb-4">Корзина пуста</p>
        <Link to="/" className="text-indigo-600 hover:underline">
          В каталог
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Корзина</h1>
      <ul className="divide-y divide-gray-200 border-y border-gray-200">
        {items.map((item) => (
          <li key={item.productId} className="flex items-center justify-between py-3">
            <span>{item.name}</span>
            <div className="flex items-center gap-4">
              <span className="text-indigo-600 font-medium">{formatPrice(item.price)}</span>
              <button
                type="button"
                aria-label={`Удалить ${item.name}`}
                onClick={() => remove(item.productId)}
                className="text-red-600 hover:underline text-sm"
              >
                Удалить
              </button>
            </div>
          </li>
        ))}
      </ul>
      <p className="text-xl font-semibold mt-6">Итого: {formatPrice(total)}</p>
      {error && <p className="text-red-600 mt-4">{error}</p>}
      <button
        type="button"
        disabled={loading}
        onClick={handleCheckout}
        className="mt-6 bg-indigo-600 text-white px-6 py-3 rounded font-medium hover:bg-indigo-700 disabled:opacity-50"
      >
        {loading ? "Создаём заказ…" : "Оформить заказ"}
      </button>
    </div>
  );
}
