import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";

import { useIsAuthed } from "../stores/auth";

export default function RequireAuth({ children }: { children: ReactNode }) {
  const isAuthed = useIsAuthed();
  const location = useLocation();

  if (!isAuthed) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <>{children}</>;
}
