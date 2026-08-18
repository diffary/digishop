import { Link, Outlet } from "react-router";

import { useAuthStore } from "../stores/auth";

export default function Layout() {
  const email = useAuthStore((state) => state.email);
  const logout = useAuthStore((state) => state.logout);

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 text-gray-900">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-indigo-600">
            DigiShop
          </Link>
          <nav className="flex items-center gap-6 text-sm">
            <Link to="/" className="hover:text-indigo-600">
              Каталог
            </Link>
            <Link to="/cart" className="hover:text-indigo-600">
              Корзина <span className="ml-1 rounded-full bg-indigo-600 text-white px-2 py-0.5 text-xs">0</span>
            </Link>
            {email ? (
              <>
                <Link to="/account" className="hover:text-indigo-600">
                  Кабинет
                </Link>
                <span className="text-gray-500">{email}</span>
                <button type="button" onClick={logout} className="hover:text-indigo-600">
                  Выйти
                </button>
              </>
            ) : (
              <Link to="/login" className="hover:text-indigo-600">
                Войти
              </Link>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-5xl mx-auto px-4 py-8 w-full">
        <Outlet />
      </main>
      <footer className="border-t border-gray-200 py-4 text-center text-xs text-gray-400">
        DigiShop — учебный проект
      </footer>
    </div>
  );
}
