import { FileText, Lock, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import { useAuth } from "../auth/AuthContext";

const FEATURES = [
  { icon: Sparkles, label: "Grounded answers" },
  { icon: FileText, label: "Cited sources" },
  { icon: Lock, label: "Private & local" },
];

export function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("demo12345");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password);
    } catch {
      setError("Invalid username or password");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-16">
      <div className="w-full max-w-[420px] animate-rise">
        <div className="mb-9 text-center">
          <div className="mx-auto mb-7 grid h-16 w-16 animate-float place-items-center rounded-[1.25rem] brand-gradient shadow-glow-lg">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-balance text-5xl font-semibold leading-[1.05] tracking-tight">
            Ask your <span className="text-gradient">documents</span> anything.
          </h1>
          <p className="mx-auto mt-4 max-w-sm text-[17px] leading-relaxed text-muted-foreground">
            Upload a PDF and get instant, grounded answers — with citations you can trust.
          </p>
        </div>

        <div className="glass rounded-3xl p-7 shadow-card">
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Username</label>
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                className="h-12 bg-background/40"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Password</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className="h-12 bg-background/40"
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={busy} size="lg" className="h-12 w-full text-[15px] shadow-glow">
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </div>

        <div className="mt-7 flex items-center justify-center gap-x-5 gap-y-2 text-[13px] text-muted-foreground">
          {FEATURES.map(({ icon: Icon, label }) => (
            <span key={label} className="flex items-center gap-1.5">
              <Icon className="h-3.5 w-3.5 text-primary" />
              {label}
            </span>
          ))}
        </div>

        <p className="mt-6 text-center text-[13px] text-muted-foreground/80">
          Demo — <span className="font-medium text-foreground">demo</span> /{" "}
          <span className="font-medium text-foreground">demo12345</span>
        </p>
      </div>
    </div>
  );
}
