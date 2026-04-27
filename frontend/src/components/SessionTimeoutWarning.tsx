import { useAuth } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

export function SessionTimeoutWarning() {
  const { showTimeoutWarning, extendSession, logout } = useAuth();

  if (!showTimeoutWarning) return null;

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm">
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 shadow-lg">
        <div className="flex items-start">
          <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5 mr-3 shrink-0" />
          <div className="flex-1">
            <h3 className="text-sm font-medium text-yellow-800">
              Session Timeout Warning
            </h3>
            <p className="text-sm text-yellow-700 mt-1">
              Your session will expire in 5 minutes due to inactivity. Click "Stay Logged In" to extend your session.
            </p>
            <div className="mt-3 flex space-x-2">
              <Button
                size="sm"
                onClick={extendSession}
                className="bg-yellow-600 hover:bg-yellow-700 text-white"
              >
                Stay Logged In
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={logout}
                className="border-yellow-300 text-yellow-700 hover:bg-yellow-50"
              >
                Logout Now
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}