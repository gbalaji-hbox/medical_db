import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/store/auth";
import { ThemeProvider } from "@/store/theme";
import { Layout } from "@/components/layout/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Toaster } from "@/components/ui/toaster";

import { LoginPage } from "@/pages/Login";
import { DashboardPage } from "@/pages/Dashboard";
import { UploadPage } from "@/pages/Upload";
import { JobsPage } from "@/pages/Jobs";
import { AutomationPage } from "@/pages/Automation";
import { ApiKeysPage } from "@/pages/admin/ApiKeys";
import { UsersPage } from "@/pages/admin/Users";
import { AuditPage } from "@/pages/admin/Audit";
import { AuditDetailPage } from "@/pages/admin/AuditDetail";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
      <AuthProvider>
        <BrowserRouter basename={import.meta.env.BASE_URL}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="upload" element={<UploadPage />} />
                <Route path="jobs" element={<JobsPage />} />
                <Route path="automation" element={<AutomationPage />} />

                {/* Admin-only routes */}
                <Route element={<ProtectedRoute adminOnly />}>
                  <Route path="admin/api-keys" element={<ApiKeysPage />} />
                  <Route path="admin/users" element={<UsersPage />} />
                  <Route path="admin/audit" element={<AuditPage />} />
                  <Route path="admin/audit/:logId" element={<AuditDetailPage />} />
                </Route>
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster />
      </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
