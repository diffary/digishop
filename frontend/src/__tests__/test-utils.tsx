import type { ReactElement } from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import type { InitialEntry } from "react-router";

export function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "Error",
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response;
}

export function renderWithProviders(
  ui: ReactElement,
  { initialEntries = ["/"] }: { initialEntries?: InitialEntry[] } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}
