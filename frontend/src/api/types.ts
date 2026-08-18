export interface TokenOut {
  access_token: string;
  token_type: string;
}

export interface UserOut {
  id: number;
  email: string;
}

export interface ProductOut {
  id: number;
  name: string;
  slug: string;
  description: string;
  price: number;
  image_url: string | null;
  category_slug: string;
}

export interface CategoryOut {
  id: number;
  name: string;
  slug: string;
}

export interface OrderItemOut {
  product_id: number;
  price_at_purchase: number;
  product_name: string;
  download_token: string | null;
}

export interface OrderOut {
  id: number;
  status: "pending" | "paid" | "delivered" | "failed";
  total: number;
  created_at: string;
  items: OrderItemOut[];
}

export interface OrderCreateOut {
  order_id: number;
  checkout_url: string;
}
