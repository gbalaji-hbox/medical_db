import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoaderProps {
  className?: string;
  size?: number;
  text?: string;
}

export function Loader({ className, size = 20, text }: LoaderProps) {
  return (
    <div className={cn("flex items-center gap-2 text-muted-foreground", className)}>
      <Loader2 size={size} className="animate-spin" />
      {text && <span className="text-sm">{text}</span>}
    </div>
  );
}

export function PageLoader({ text = "Loading…" }: { text?: string }) {
  return (
    <div className="flex h-[60vh] items-center justify-center">
      <Loader size={28} text={text} />
    </div>
  );
}
