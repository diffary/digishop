import { BrowserRouter, Route, Routes } from "react-router";

import Layout from "./components/Layout";
import Account from "./pages/Account";
import AuthCallback from "./pages/AuthCallback";
import Cart from "./pages/Cart";
import Catalog from "./pages/Catalog";
import Login from "./pages/Login";
import OrderCancel from "./pages/OrderCancel";
import OrderSuccess from "./pages/OrderSuccess";
import Product from "./pages/Product";
import Register from "./pages/Register";

// Маршруты вынесены отдельно, чтобы тесты могли рендерить их в MemoryRouter
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Catalog />} />
        <Route path="/product/:slug" element={<Product />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/account" element={<Account />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/order/success" element={<OrderSuccess />} />
        <Route path="/order/cancel" element={<OrderCancel />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
