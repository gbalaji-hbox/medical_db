import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/store/auth";
import { PageLoader } from "@/components/ui/loader";

export function ProtectedRoute({ adminOnly = false }: { adminOnly?: boolean }) {
  const { user, isLoading } = useAuth();

  if (isLoading) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/dashboard" replace />;

  return <Outlet />;
}
