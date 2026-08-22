import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import { get, post } from "../api/client";
import type { TokenOut, UserOut } from "../api/types";
import { useAuthStore } from "../stores/auth";

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const [error, setError] = useState(false);
  const setAuth = useAuthStore((state) => state.setAuth);
  const navigate = useNavigate();
  const exchangedRef = useRef(false);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setError(true);
      return;
    }
    // Код одноразовый: повторный обмен (например, из-за двойного
    // срабатывания эффекта в React StrictMode) вернул бы 400 и разлогинил
    // бы уже вошедшего пользователя — гардим ref'ом, выставленным ДО await.
    if (exchangedRef.current) {
      return;
    }
    exchangedRef.current = true;

    (async () => {
      try {
        const tokenData = await post<TokenOut>("/auth/exchange", { code });
        // /auth/exchange не возвращает email — GET /auth/me требует
        // Authorization-заголовок, поэтому сперва кладём токен в стор,
        // чтобы api/client подставил его сам, затем дотягиваем email.
        setAuth(tokenData.access_token, "");
        try {
          const me = await get<UserOut>("/auth/me");
          setAuth(tokenData.access_token, me.email);
        } catch {
          // Токен уже валиден (обмен прошёл) — не откатываем логин,
          // просто останемся без email, если /auth/me недоступен.
        }
        navigate("/", { replace: true });
      } catch {
        setError(true);
      }
    })();
  }, [searchParams, setAuth, navigate]);

  if (error) {
    return (
      <div className="flex justify-center py-8">
        <div className="w-full max-w-sm bg-white rounded-lg border border-gray-200 p-6 shadow-sm text-center">
          <h1 className="text-xl font-semibold mb-4 text-red-600">
            Не удалось войти через Google
          </h1>
          <Link to="/login" className="text-indigo-600 hover:underline">
            Попробовать ещё раз
          </Link>
        </div>
      </div>
    );
  }

  return <h1 className="text-2xl font-semibold">Входим…</h1>;
}
