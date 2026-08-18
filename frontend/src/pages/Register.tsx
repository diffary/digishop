import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router";

import { ApiError, post } from "../api/client";
import type { TokenOut, UserOut } from "../api/types";
import { useAuthStore } from "../stores/auth";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const setAuth = useAuthStore((state) => state.setAuth);
  const navigate = useNavigate();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Пароль должен содержать не менее 8 символов");
      return;
    }

    setLoading(true);
    try {
      await post<UserOut>("/auth/register", { email, password });
      const data = await post<TokenOut>("/auth/login", { email, password });
      setAuth(data.access_token, email);
      navigate("/");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError("Этот email уже зарегистрирован");
        } else if (err.status === 429) {
          setError("Слишком много попыток, подождите минуту");
        } else {
          setError(err.detail);
        }
      } else {
        setError("Не удалось выполнить регистрацию");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex justify-center py-8">
      <div className="w-full max-w-sm bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h1 className="text-2xl font-semibold mb-6 text-center">Регистрация</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label htmlFor="register-email" className="text-sm text-gray-700">
              Email
            </label>
            <input
              id="register-email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="register-password" className="text-sm text-gray-700">
              Пароль
            </label>
            <input
              id="register-password"
              type="password"
              required
              minLength={8}
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
            Зарегистрироваться
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-600">
          Уже есть аккаунт?{" "}
          <Link to="/login" className="text-indigo-600 hover:underline">
            Войти
          </Link>
        </p>
      </div>
    </div>
  );
}
