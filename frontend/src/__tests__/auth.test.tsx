import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { AppRoutes } from "../App";
import { useAuthStore } from "../stores/auth";
import { renderWithProviders } from "./test-utils";

beforeEach(() => {
  useAuthStore.setState({ token: null, email: null });
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn());
});

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "Error",
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response;
}

async function fillLoginForm(email: string, password: string) {
  fireEvent.change(screen.getByLabelText(/email/i), { target: { value: email } });
  fireEvent.change(screen.getByLabelText(/пароль/i), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Войти" }));
}

test("успешный логин сохраняет токен и переходит на другую страницу", async () => {
  const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;
  mockFetch.mockImplementation((url: string) => {
    if (url.includes("/categories")) return Promise.resolve(jsonResponse(200, []));
    if (url.includes("/products")) return Promise.resolve(jsonResponse(200, []));
    return Promise.resolve(jsonResponse(200, { access_token: "tok123", token_type: "bearer" }));
  });

  renderWithProviders(<AppRoutes />, { initialEntries: ["/login"] });

  await fillLoginForm("user@example.com", "password1");

  await waitFor(() => {
    expect(useAuthStore.getState().token).toBe("tok123");
  });
  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "Каталог" })).toBeInTheDocument();
  });
});

test("логин с 401 показывает текст ошибки", async () => {
  const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;
  mockFetch.mockResolvedValueOnce(jsonResponse(401, { detail: "Invalid credentials" }));

  renderWithProviders(<AppRoutes />, { initialEntries: ["/login"] });

  await fillLoginForm("user@example.com", "wrongpass");

  expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
});

test("регистрация делает запрос регистрации, затем логина, и сохраняет токен", async () => {
  const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;
  mockFetch
    .mockResolvedValueOnce(jsonResponse(201, { id: 1, email: "new@example.com" }))
    .mockResolvedValueOnce(jsonResponse(200, { access_token: "tok456", token_type: "bearer" }));

  renderWithProviders(<AppRoutes />, { initialEntries: ["/register"] });

  fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "new@example.com" } });
  fireEvent.change(screen.getByLabelText(/пароль/i), { target: { value: "password1" } });
  fireEvent.click(screen.getByRole("button", { name: /зарегистрироваться/i }));

  await waitFor(() => {
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
  await waitFor(() => {
    expect(useAuthStore.getState().token).toBe("tok456");
  });
});

test("Login читает location.state.from и перенаправляет туда после успеха", async () => {
  const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>;
  mockFetch.mockImplementation((url: string) => {
    if (url.includes("/products")) return Promise.resolve(jsonResponse(200, []));
    return Promise.resolve(jsonResponse(200, { access_token: "tok789", token_type: "bearer" }));
  });

  renderWithProviders(<AppRoutes />, {
    initialEntries: [{ pathname: "/login", state: { from: "/cart" } }],
  });

  await fillLoginForm("user@example.com", "password1");

  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "Корзина" })).toBeInTheDocument();
  });
});
