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
          "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
          isActive
            ? "bg-primary text-primary-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
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
    <span className="flex items-center gap-2 text-lg font-bold tracking-tight">
      <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground">
        D
      </span>
      Docu<span className="text-primary">Mind</span>
    </span>
  );
}

export default function App() {
  const { isAuthenticated, logout } = useAuth();

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <div className="absolute right-4 top-4">
          <ThemeToggle />
        </div>
        <LoginPage />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
        <div className="container flex h-14 items-center justify-between">
          <Brand />
          <nav className="flex items-center gap-1">
            <NavTab to="/upload" label="Upload" icon={<FileText className="h-4 w-4" />} />
            <NavTab to="/ask" label="Ask" icon={<MessagesSquare className="h-4 w-4" />} />
            <ThemeToggle />
            <Button variant="ghost" size="sm" onClick={logout} className="text-muted-foreground">
              Sign out
            </Button>
          </nav>
        </div>
      </header>

      <main className="container py-8">
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/ask" element={<AskPage />} />
        </Routes>
      </main>
    </div>
  );
}
