import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";

import { API_URL, ApiError, post } from "../api/client";
import type { TokenOut } from "../api/types";
import { useAuthStore } from "../stores/auth";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const setAuth = useAuthStore((state) => state.setAuth);
  const navigate = useNavigate();
  const location = useLocation();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await post<TokenOut>("/auth/login", { email, password });
      setAuth(data.access_token, email);
      const from = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(from);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 429) {
          setError("Слишком много попыток, подождите минуту");
        } else {
          setError(err.detail);
        }
      } else {
        setError("Не удалось выполнить вход");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex justify-center py-8">
      <div className="w-full max-w-sm bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h1 className="text-2xl font-semibold mb-6 text-center">Вход</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label htmlFor="login-email" className="text-sm text-gray-700">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="login-password" className="text-sm text-gray-700">
              Пароль
            </label>
            <input
              id="login-password"
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="bg-indigo-600 text-white rounded px-3 py-2 text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            Войти
          </button>
        </form>
        <button
          type="button"
          onClick={() => {
            window.location.href = `${API_URL}/auth/google`;
          }}
          className="mt-3 w-full border border-gray-300 rounded px-3 py-2 text-sm font-medium hover:bg-gray-50"
        >
          Войти через Google
        </button>
        <p className="mt-4 text-center text-sm text-gray-600">
          Нет аккаунта?{" "}
          <Link to="/register" className="text-indigo-600 hover:underline">
            Регистрация
          </Link>
        </p>
      </div>
    </div>
  );
}
