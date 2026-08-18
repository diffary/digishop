import { useQuery } from "@tanstack/react-query";

import { get } from "./client";
import type { CategoryOut, ProductOut } from "./types";

export function useProducts(params: { category?: string; search?: string }) {
  const search = new URLSearchParams();
  if (params.category) search.set("category", params.category);
  if (params.search) search.set("search", params.search);
  const qs = search.toString();

  return useQuery({
    queryKey: ["products", params.category ?? "", params.search ?? ""],
    queryFn: () => get<ProductOut[]>(`/products${qs ? `?${qs}` : ""}`),
  });
}

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: () => get<CategoryOut[]>("/categories"),
  });
}

export function useProduct(slug: string) {
  return useQuery({
    queryKey: ["product", slug],
    queryFn: () => get<ProductOut>(`/products/${slug}`),
    retry: false,
  });
}
