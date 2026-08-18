import { Link, useParams } from "react-router";

import { useProduct } from "../api/catalog";
import { ApiError } from "../api/client";
import { formatPrice } from "../lib/format";
import { useCartStore } from "../stores/cart";

export default function Product() {
  const { slug = "" } = useParams();
  const { data: product, isLoading, error } = useProduct(slug);
  const add = useCartStore((state) => state.add);
  const inCart = useCartStore((state) =>
    product ? state.items.some((i) => i.productId === product.id) : false,
  );

  if (isLoading) {
    return <p className="text-gray-500">Загрузка...</p>;
  }

  if (error instanceof ApiError && error.status === 404) {
    return (
      <div>
        <p className="text-lg mb-4">Товар не найден</p>
        <Link to="/" className="text-indigo-600 hover:underline">
          ← В каталог
        </Link>
      </div>
    );
  }

  if (error || !product) {
    return <p className="text-red-600">Не удалось загрузить товар</p>;
  }

  return (
    <div>
      <Link to="/" className="text-indigo-600 hover:underline text-sm">
        ← В каталог
      </Link>
      <h1 className="text-2xl font-semibold mt-3">{product.name}</h1>
      <p className="text-gray-600 mt-2">{product.description}</p>
      <p className="text-xl font-semibold text-indigo-600 mt-4">{formatPrice(product.price)}</p>
      <button
        type="button"
        disabled={inCart}
        onClick={() =>
          add({ productId: product.id, slug: product.slug, name: product.name, price: product.price })
        }
        className="mt-6 bg-indigo-600 text-white px-6 py-3 rounded font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {inCart ? "В корзине ✓" : "В корзину"}
      </button>
    </div>
  );
}
