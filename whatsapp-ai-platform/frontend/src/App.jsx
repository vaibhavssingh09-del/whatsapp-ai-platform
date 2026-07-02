import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import DashboardLayout from "./components/DashboardLayout";
import LoginPage from "./pages/LoginPage";
import ConversationMonitorPage from "./pages/ConversationMonitorPage";
import MediaLibraryPage from "./pages/MediaLibraryPage";
import BroadcastsPage from "./pages/BroadcastsPage";
import MetricsPage from "./pages/MetricsPage";
import AuditLogsPage from "./pages/AuditLogsPage";

function ProtectedRoute({ children }) {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-ink-50 text-ink-500">
        Loading…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/conversations" replace />} />
        <Route path="conversations" element={<ConversationMonitorPage />} />
        <Route path="media" element={<MediaLibraryPage />} />
        <Route path="broadcasts" element={<BroadcastsPage />} />
        <Route path="metrics" element={<MetricsPage />} />
        <Route path="audit-logs" element={<AuditLogsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
