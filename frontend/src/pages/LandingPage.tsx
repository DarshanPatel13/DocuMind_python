import {
  ArrowRight,
  BookOpen,
  Gauge,
  Lock,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import { useRef, useState, type FormEvent, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

import { useAuth } from "../auth/AuthContext";

/* ---------- small building blocks ---------- */

function Overline({ children }: { children: ReactNode }) {
  return (
    <p className="mb-3 text-sm font-semibold uppercase tracking-[0.12em] text-primary">{children}</p>
  );
}

function LinkPill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 text-[17px] font-medium text-primary transition-opacity hover:opacity-80">
      {children} <ArrowRight className="h-4 w-4" />
    </span>
  );
}

function DeviceFrame({ src, alt }: { src: string; alt: string }) {
  return (
    <div className="mx-auto mt-10 max-w-3xl overflow-hidden rounded-2xl border border-border/60 bg-card shadow-card ring-1 ring-black/5">
      <div className="flex h-8 items-center gap-1.5 border-b border-border/60 bg-secondary/60 px-4">
        <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" />
        <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
      </div>
      <img src={src} alt={alt} className="block w-full" loading="lazy" />
    </div>
  );
}

function FeatureTile({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof Sparkles;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="group rounded-3xl border border-border/60 bg-card p-8 shadow-soft transition-all duration-300 hover:-translate-y-1 hover:shadow-card">
      <div className="mb-5 grid h-12 w-12 place-items-center rounded-2xl brand-gradient text-white shadow-glow transition-transform duration-300 group-hover:scale-110">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-xl font-semibold tracking-tight">{title}</h3>
      <p className="mt-2 leading-relaxed text-muted-foreground">{children}</p>
    </div>
  );
}

function Section({
  alt = false,
  className,
  children,
}: {
  alt?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={cn("w-full px-5 py-20 sm:py-28", alt && "bg-surface-alt", className)}>
      <div className="container">{children}</div>
    </section>
  );
}

/* ---------- the page ---------- */

export function LandingPage() {
  const { login } = useAuth();
  const loginRef = useRef<HTMLDivElement>(null);
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

  const scrollToLogin = () =>
    loginRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });

  return (
    <div>
      {/* ---------------- HERO ---------------- */}
      <section className="relative overflow-hidden px-5 pb-16 pt-20 text-center sm:pt-28">
        <div className="container">
          <div className="mx-auto mb-7 inline-flex animate-rise items-center gap-2 rounded-full border bg-card/70 px-4 py-1.5 text-sm font-medium text-muted-foreground backdrop-blur">
            <Sparkles className="h-4 w-4 text-primary" />
            Answers grounded in your files
          </div>
          <h1 className="mx-auto max-w-4xl text-balance text-6xl font-semibold leading-[1.04] tracking-tight sm:text-7xl">
            Ask your <span className="text-gradient">documents</span> anything.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-xl leading-relaxed text-muted-foreground">
            Upload a PDF. Get instant answers — grounded in your files, cited, and private.
            Free to run entirely on your own machine.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Button size="lg" className="h-12 px-7 text-[15px] shadow-glow" onClick={scrollToLogin}>
              Get started
            </Button>
            <a href="#latest">
              <Button size="lg" variant="outline" className="h-12 px-7 text-[15px]">
                See it in action
              </Button>
            </a>
          </div>

          {/* Sign-in card */}
          <div ref={loginRef} className="mx-auto mt-14 max-w-sm scroll-mt-24">
            <div className="glass rounded-3xl p-7 text-left shadow-card">
              <h2 className="mb-1 text-lg font-semibold">Sign in to DocuMind</h2>
              <p className="mb-5 text-sm text-muted-foreground">
                Demo — <span className="font-medium text-foreground">demo</span> /{" "}
                <span className="font-medium text-foreground">demo12345</span>
              </p>
              <form onSubmit={onSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium">Username</label>
                  <Input
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                    className="h-11 bg-background/50"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium">Password</label>
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    className="h-11 bg-background/50"
                  />
                </div>
                {error && <p className="text-sm text-destructive">{error}</p>}
                <Button type="submit" disabled={busy} size="lg" className="h-11 w-full shadow-glow">
                  {busy ? "Signing in…" : "Sign in"}
                </Button>
              </form>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- THE LATEST ---------------- */}
      <Section alt className="text-center">
        <div id="latest" className="scroll-mt-20">
          <Overline>The latest</Overline>
          <h2 className="mx-auto max-w-3xl text-balance text-5xl font-semibold leading-[1.06] tracking-tight">
            Take a look at <span className="text-gradient">what's new</span>, right now.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-muted-foreground">
            Answers stream in token-by-token, each claim carries a clickable citation, and one
            tap reveals the exact source passage.
          </p>
          <DeviceFrame src="/marketing/product-ask.png" alt="DocuMind answering a question with a citation" />
        </div>
      </Section>

      {/* ---------------- BENTO FEATURES ---------------- */}
      <Section>
        <div className="mb-12 text-center">
          <h2 className="text-balance text-5xl font-semibold tracking-tight">
            Designed to be trusted.
          </h2>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          <FeatureTile icon={Sparkles} title="Grounded, never guessing.">
            Answers come only from your documents. If the answer isn't there, DocuMind says so —
            no hallucinations.
          </FeatureTile>
          <FeatureTile icon={Lock} title="Private &amp; local.">
            Run the whole pipeline offline with Ollama — no API keys, no data leaving your machine,
            $0 to operate.
          </FeatureTile>
          <FeatureTile icon={Gauge} title="Built to scale.">
            Independent microservices, Kafka-based ingestion, hybrid retrieval with reranking, and
            full observability.
          </FeatureTile>
        </div>
      </Section>

      {/* ---------------- HELP / DOCS ---------------- */}
      <Section alt>
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <div>
            <Overline>Documentation</Overline>
            <h2 className="text-balance text-5xl font-semibold leading-[1.06] tracking-tight">
              Help is here. Whenever and however you need it.
            </h2>
            <p className="mt-4 max-w-lg text-lg text-muted-foreground">
              A high-level design doc, per-service guides, a Java→Python glossary, an interview
              cheatsheet, and a five-minute runbook — all in the repo.
            </p>
            <div className="mt-7 flex flex-wrap gap-x-8 gap-y-3">
              <LinkPill>
                <BookOpen className="h-4 w-4" /> Read the HLD
              </LinkPill>
              <LinkPill>
                <ScrollText className="h-4 w-4" /> Browse the docs
              </LinkPill>
            </div>
          </div>
          <DeviceFrame src="/marketing/product-upload.png" alt="DocuMind upload and document list" />
        </div>
      </Section>

      {/* ---------------- THE DIFFERENCE ---------------- */}
      <Section className="text-center">
        <h2 className="text-balance text-5xl font-semibold tracking-tight">
          The DocuMind difference.
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-lg text-muted-foreground">
          Even more reasons to build on it.
        </p>
        <div className="mt-14 grid gap-10 sm:grid-cols-3">
          {[
            { icon: Zap, title: "Evaluated.", body: "Retrieval + Ragas quality metrics you can run with one command." },
            { icon: Gauge, title: "Observable.", body: "Every LLM call traced — prompt, tokens, cost, and latency." },
            { icon: ShieldCheck, title: "Guarded.", body: "Grounded-only answering plus prompt-injection screening." },
          ].map(({ icon: Icon, title, body }) => (
            <div key={title} className="flex flex-col items-center">
              <div className="mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-secondary text-primary">
                <Icon className="h-7 w-7" />
              </div>
              <h3 className="text-2xl font-semibold tracking-tight">{title}</h3>
              <p className="mt-2 max-w-xs text-muted-foreground">{body}</p>
            </div>
          ))}
        </div>
        <div className="mt-16">
          <Button size="lg" className="h-12 px-8 text-[15px] shadow-glow" onClick={scrollToLogin}>
            Get started — it's free
          </Button>
        </div>
      </Section>

      {/* ---------------- FOOTER ---------------- */}
      <footer className="border-t border-border/60 px-5 py-10 text-center text-sm text-muted-foreground">
        <p className="flex items-center justify-center gap-2 font-medium text-foreground">
          <span className="grid h-6 w-6 place-items-center rounded-md brand-gradient text-white">
            <Sparkles className="h-3.5 w-3.5" />
          </span>
          DocuMind
        </p>
        <p className="mt-2">Document intelligence. Grounded. Cited. Private.</p>
      </footer>
    </div>
  );
}
