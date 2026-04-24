import { Link, useNavigate } from "react-router-dom";
import { Menu, LogOut, Shield, Sun, Moon } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/store/auth";
import { useTheme } from "@/store/theme";

export function TopNav({ onMenuClick }: { onMenuClick?: () => void }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();

  const initials = user?.username
    ? user.username.slice(0, 2).toUpperCase()
    : "??";

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center border-b bg-background px-4 gap-4">
      {onMenuClick && (
        <Button variant="ghost" size="icon" onClick={onMenuClick} className="lg:hidden">
          <Menu size={20} />
        </Button>
      )}

      {/* Logo — provision for image asset */}
      <Link to="/dashboard" className="flex items-center gap-2 font-semibold text-primary shrink-0">
        <div className="flex h-7 w-7 items-center justify-center rounded bg-primary text-primary-foreground text-xs font-bold">
          H
        </div>
        <span className="hidden sm:inline">HBox Medical ETL</span>
      </Link>

      <div className="ml-auto flex items-center gap-2">
        {user?.role === "admin" && (
          <Badge variant="secondary" className="hidden sm:flex gap-1">
            <Shield size={11} />
            Admin
          </Badge>
        )}

        {/* Dark / light mode toggle */}
        <Button variant="ghost" size="icon" onClick={toggle} title="Toggle theme">
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </Button>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-8 w-8 rounded-full p-0">
              <Avatar>
                <AvatarFallback>{initials}</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel className="font-normal">
              <p className="font-semibold">{user?.username}</p>
              <p className="text-xs text-muted-foreground capitalize">{user?.role}</p>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {user?.role === "admin" && (
              <>
                <DropdownMenuItem onClick={() => navigate("/admin/users")}>
                  Users
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate("/admin/api-keys")}>
                  API Keys
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate("/admin/audit")}>
                  Audit Log
                </DropdownMenuItem>
                <DropdownMenuSeparator />
              </>
            )}
            <DropdownMenuItem
              onClick={() => { logout(); navigate("/login"); }}
              className="text-destructive focus:text-destructive"
            >
              <LogOut size={14} className="mr-2" />
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
