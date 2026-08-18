import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { expect, test } from "vitest";

import { AppRoutes } from "../App";

test("шапка показывает навигацию", () => {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <AppRoutes />
    </MemoryRouter>,
  );
  expect(screen.getByRole("link", { name: "Каталог" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Корзина/ })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Войти" })).toBeInTheDocument();
});

test("страница каталога рендерится на корне", () => {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <AppRoutes />
    </MemoryRouter>,
  );
  expect(screen.getByRole("heading", { name: "Каталог" })).toBeInTheDocument();
});
