import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "../api/client";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (count, err) =>
        !(err instanceof ApiError && err.status >= 400 && err.status < 500) && count < 3,
    },
  },
});
