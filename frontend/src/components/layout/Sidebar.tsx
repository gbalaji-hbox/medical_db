import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  FolderOpen,
  Users,
  KeyRound,
  ClipboardList,
  Bot,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/store/auth";
import { Separator } from "@/components/ui/separator";

function NavItem({
  to,
  icon: Icon,
  label,
  end = false,
}: {
  to: string;
  icon: React.ElementType;
  label: string;
  end?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-primary text-primary-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        )
      }
    >
      <Icon size={16} />
      {label}
    </NavLink>
  );
}

export function Sidebar({ onClose }: { onClose?: () => void }) {
  const { user } = useAuth();

  return (
    <nav
      className="flex h-full w-56 flex-col gap-1 bg-background px-2 py-4"
      onClick={onClose}
    >
      <NavItem to="/dashboard" icon={LayoutDashboard} label="Dashboard" end />
      <NavItem to="/upload" icon={Upload} label="Upload" />
      <NavItem to="/jobs" icon={FolderOpen} label="Jobs" />
      <NavItem to="/automation" icon={Bot} label="Automation" />

      {user?.role === "admin" && (
        <>
          <Separator className="my-2" />
          <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Admin
          </p>
          <NavItem to="/admin/users" icon={Users} label="Users" />
          <NavItem to="/admin/api-keys" icon={KeyRound} label="API Keys" />
          <NavItem to="/admin/audit" icon={ClipboardList} label="Audit Log" />
        </>
      )}
    </nav>
  );
}
