import { FileText, MessagesSquare } from "lucide-react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { useAuth } from "./auth/AuthContext";
import { AskPage } from "./pages/AskPage";
import { LoginPage } from "./pages/LoginPage";
import { UploadPage } from "./pages/UploadPage";

function NavTab({ to, label, icon }: { to: string; label: string; icon: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          "inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-medium transition-all",
          isActive
            ? "bg-card text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground",
        )
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}

function Brand() {
  return (
    <span className="flex items-center gap-2 text-[17px] font-semibold tracking-tight">
      <span className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-primary to-primary/70 text-[15px] font-bold text-primary-foreground shadow-glow">
        D
      </span>
      DocuMind
    </span>
  );
}

export default function App() {
  const { isAuthenticated, logout } = useAuth();

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <div className="absolute right-5 top-5 z-10">
          <ThemeToggle />
        </div>
        <LoginPage />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-border/70 bg-background/70 backdrop-blur-xl supports-[backdrop-filter]:bg-background/55">
        <div className="container flex h-14 items-center justify-between">
          <Brand />
          <div className="flex items-center gap-2">
            <nav className="flex items-center gap-1 rounded-full bg-secondary/70 p-1">
              <NavTab to="/upload" label="Upload" icon={<FileText className="h-4 w-4" />} />
              <NavTab to="/ask" label="Ask" icon={<MessagesSquare className="h-4 w-4" />} />
            </nav>
            <ThemeToggle />
            <Button variant="ghost" size="sm" onClick={logout} className="text-muted-foreground">
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="container animate-rise py-10">
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/ask" element={<AskPage />} />
        </Routes>
      </main>
    </div>
  );
}
