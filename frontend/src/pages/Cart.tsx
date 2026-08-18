import { Link } from "react-router";

import { formatPrice } from "../lib/format";
import { useCartStore, useCartTotal } from "../stores/cart";

export default function Cart() {
  const items = useCartStore((state) => state.items);
  const remove = useCartStore((state) => state.remove);
  const total = useCartTotal();

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
      <button
        type="button"
        onClick={() => console.log("checkout")}
        className="mt-6 bg-indigo-600 text-white px-6 py-3 rounded font-medium hover:bg-indigo-700"
      >
        Оформить заказ
      </button>
    </div>
  );
}
