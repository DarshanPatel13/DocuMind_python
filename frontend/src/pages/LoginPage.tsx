import { Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import { useAuth } from "../auth/AuthContext";

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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      {/* Ambient gradient wash */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute left-1/2 top-[-10%] h-[480px] w-[480px] -translate-x-1/2 rounded-full bg-primary/20 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[10%] h-[360px] w-[360px] rounded-full bg-primary/10 blur-[120px]" />
      </div>

      <div className="w-full max-w-[400px] animate-rise">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-primary to-primary/70 shadow-glow">
            <Sparkles className="h-7 w-7 text-primary-foreground" />
          </div>
          <h1 className="text-[28px] font-semibold tracking-tight">Welcome to DocuMind</h1>
          <p className="mt-1.5 text-[15px] text-muted-foreground">
            Ask anything about your documents.
          </p>
        </div>

        <div className="rounded-3xl border bg-card/80 p-7 shadow-card backdrop-blur-xl">
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Username</label>
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                className="h-11"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Password</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className="h-11"
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={busy} size="lg" className="w-full">
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </div>

        <p className="mt-5 text-center text-[13px] text-muted-foreground">
          Demo access — <span className="font-medium text-foreground">demo</span> /{" "}
          <span className="font-medium text-foreground">demo12345</span>
        </p>
      </div>
    </div>
  );
}
