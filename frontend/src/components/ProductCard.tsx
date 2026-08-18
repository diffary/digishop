import { Link } from "react-router";

import { formatPrice } from "../lib/format";
import type { ProductOut } from "../api/types";

export default function ProductCard({ product }: { product: ProductOut }) {
  return (
    <Link
      to={`/product/${product.slug}`}
      className="block border border-gray-200 rounded-lg overflow-hidden bg-white hover:shadow-md transition-shadow"
    >
      {product.image_url ? (
        <img src={product.image_url} alt={product.name} className="w-full h-40 object-cover" />
      ) : (
        <div className="w-full h-40 bg-gray-200" aria-hidden="true" />
      )}
      <div className="p-3">
        <p className="text-xs text-gray-500">{product.category_slug}</p>
        <h3 className="font-medium">{product.name}</h3>
        <p className="mt-1 font-semibold text-indigo-600">{formatPrice(product.price)}</p>
      </div>
    </Link>
  );
}
