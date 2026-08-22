import { Link } from "react-router";

export default function OrderCancel() {
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Оплата отменена</h1>
      <p className="text-gray-700 mb-6">
        Заказ остался в кабинете со статусом «ожидает оплаты» и автоматически отменится через час с
        небольшим.
      </p>
      <div className="flex gap-4">
        <Link to="/account" className="text-indigo-600 hover:underline">
          В кабинет
        </Link>
        <Link to="/" className="text-indigo-600 hover:underline">
          В каталог
        </Link>
      </div>
    </div>
  );
}
