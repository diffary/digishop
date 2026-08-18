import { useEffect, useState } from "react";

import { useCategories, useProducts } from "../api/catalog";
import ProductCard from "../components/ProductCard";

export default function Catalog() {
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data: categories } = useCategories();
  const { data: products, isLoading, error } = useProducts({
    category: category || undefined,
    search: debouncedSearch || undefined,
  });

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Каталог</h1>
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <select
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          className="border border-gray-300 rounded px-3 py-2 text-sm"
        >
          <option value="">Все категории</option>
          {categories?.map((c) => (
            <option key={c.slug} value={c.slug}>
              {c.name}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Поиск..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="border border-gray-300 rounded px-3 py-2 text-sm flex-1"
        />
      </div>

      {isLoading && <p className="text-gray-500">Загрузка...</p>}
      {error && <p className="text-red-600">Не удалось загрузить каталог</p>}
      {!isLoading && !error && products && products.length === 0 && (
        <p className="text-gray-500">Ничего не найдено</p>
      )}
      {products && products.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </div>
  );
}
