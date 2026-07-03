import { CheckCircle2, ChevronDown, Gauge, Play, ShieldCheck, XCircle } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import { useEvalStatus, useRunEvals } from "../hooks/useEvals";
import type { EvalCaseResult } from "../types";

/* ---------- formatting helpers ---------- */

const pct = (value: number | null | undefined) =>
  value == null ? "—" : `${Math.round(value * 100)}%`;

const BEHAVIOR_STYLES: Record<string, string> = {
  answer: "bg-sky-500/10 text-sky-600 dark:text-sky-400",
  refuse: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  resist_injection: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
};

const BEHAVIOR_LABELS: Record<string, string> = {
  answer: "Answer",
  refuse: "Refuse",
  resist_injection: "Resist injection",
};

/* ---------- building blocks ---------- */

function MetricCard({
  label,
  value,
  threshold,
  hint,
}: {
  label: string;
  value: number | null | undefined;
  threshold: string;
  hint?: string;
}) {
  const missing = value == null;
  const failed = !missing && value < parseFloat(threshold.replace(/[^\d.]/g, "")) / 100;
  return (
    <Card
      className={cn(
        "border-border/60 transition-colors",
        !missing && (failed ? "border-red-500/40 bg-red-500/[0.04]" : "border-emerald-500/30 bg-emerald-500/[0.04]"),
      )}
    >
      <CardContent className="p-6">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <p
          className={cn(
            "mt-2 text-4xl font-semibold tracking-tight",
            !missing && (failed ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"),
          )}
        >
          {pct(value)}
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          gate {threshold}
          {missing && hint ? ` · ${hint}` : ""}
        </p>
      </CardContent>
    </Card>
  );
}

function ScoreChip({ passed, errored }: { passed: boolean; errored: boolean }) {
  if (errored) {
    return <Badge className="bg-amber-500/15 text-amber-600 dark:text-amber-400">Errored</Badge>;
  }
  return passed ? (
    <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
      <CheckCircle2 className="mr-1 h-3 w-3" /> Pass
    </Badge>
  ) : (
    <Badge className="bg-red-500/15 text-red-600 dark:text-red-400">
      <XCircle className="mr-1 h-3 w-3" /> Fail
    </Badge>
  );
}

function CaseRow({ result }: { result: EvalCaseResult }) {
  const [open, setOpen] = useState(false);
  const score =
    result.groundedness != null
      ? pct(result.groundedness)
      : result.refusal != null
        ? pct(result.refusal)
        : result.guardrail != null
          ? pct(result.guardrail)
          : "—";
  return (
    <div className="border-b border-border/50 last:border-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="grid w-full grid-cols-[1fr_auto_auto_auto_auto] items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-secondary/40 sm:gap-5"
      >
        <span className="truncate font-mono text-sm">{result.id}</span>
        <Badge className={cn("hidden sm:inline-flex", BEHAVIOR_STYLES[result.behavior])}>
          {BEHAVIOR_LABELS[result.behavior] ?? result.behavior}
        </Badge>
        <span className="w-12 text-right text-sm tabular-nums text-muted-foreground">{score}</span>
        <ScoreChip passed={result.passed} errored={result.errored} />
        <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="space-y-3 px-4 pb-4 text-sm">
          <p className="text-muted-foreground">
            <span className="font-medium text-foreground">Q — </span>
            {result.question}
          </p>
          <p className="whitespace-pre-wrap rounded-xl bg-secondary/50 p-3 leading-relaxed">
            {result.answer || "(empty answer)"}
          </p>
          {result.unsupported_claims.length > 0 && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/[0.05] p-3">
              <p className="mb-1 font-medium text-red-600 dark:text-red-400">
                Unsupported claims (per the judge)
              </p>
              <ul className="list-inside list-disc space-y-0.5 text-muted-foreground">
                {result.unsupported_claims.map((claim) => (
                  <li key={claim}>{claim}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            citations: {result.citations_valid} valid · {result.citations_invalid} invalid ·{" "}
            {result.citations_supported} judge-confirmed
          </p>
        </div>
      )}
    </div>
  );
}

function Explainer({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <Card className="border-border/60">
      <CardContent className="p-6">
        <div className="mb-3 grid h-10 w-10 place-items-center rounded-xl brand-gradient text-white shadow-glow">
          {icon}
        </div>
        <h3 className="font-semibold">{title}</h3>
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{children}</p>
      </CardContent>
    </Card>
  );
}

/* ---------- the page ---------- */

export function EvalsPage() {
  const { data, isLoading } = useEvalStatus();
  const runMutation = useRunEvals();

  const running = data?.status === "running";
  const report = data?.report ?? null;
  const aggregates = report?.aggregates ?? {};
  const progressPct =
    data?.progress && data.progress.total > 0
      ? Math.round((data.progress.done / data.progress.total) * 100)
      : 0;

  return (
    <div className="mx-auto max-w-4xl">
      {/* header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-sm font-semibold uppercase tracking-[0.12em] text-primary">
            DocuMind Labs
          </p>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">Prove it.</h1>
          <p className="mt-3 max-w-xl text-muted-foreground">
            Twelve golden questions. Four metrics. One verdict — measured against the live
            system, end to end, not on vibes.
          </p>
        </div>
        <Button
          size="lg"
          className="h-11 px-6 shadow-glow"
          disabled={running || runMutation.isPending}
          onClick={() => runMutation.mutate()}
        >
          <Play className="mr-2 h-4 w-4" />
          {running ? "Running…" : "Run evals"}
        </Button>
      </div>

      {/* run error */}
      {data?.status === "error" && (
        <Card className="mt-8 border-red-500/40 bg-red-500/[0.05]">
          <CardContent className="p-5 text-sm">
            <p className="font-medium text-red-600 dark:text-red-400">The run failed.</p>
            <p className="mt-1 text-muted-foreground">{data.error}</p>
          </CardContent>
        </Card>
      )}

      {/* live progress */}
      {running && (
        <Card className="mt-8 border-border/60">
          <CardContent className="p-6">
            <div className="flex items-center justify-between text-sm">
              <p className="font-medium">
                {data?.progress?.current
                  ? `Case ${Math.min((data.progress?.done ?? 0) + 1, data.progress?.total ?? 12)} of ${data?.progress?.total} — ${data?.progress?.current}`
                  : "Ingesting the golden document…"}
              </p>
              <p className="tabular-nums text-muted-foreground">{progressPct}%</p>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full rounded-full brand-gradient transition-all duration-700"
                style={{ width: `${Math.max(progressPct, 4)}%` }}
              />
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              Answers come from the live model; a stronger LLM judge grades every claim
              against the retrieved context.
            </p>
          </CardContent>
        </Card>
      )}

      {isLoading && (
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-36 rounded-2xl" />
          ))}
        </div>
      )}

      {/* results */}
      {report && !running && (
        <>
          <Card
            className={cn(
              "mt-8",
              report.failures.length === 0
                ? "border-emerald-500/40 bg-emerald-500/[0.05]"
                : "border-red-500/40 bg-red-500/[0.05]",
            )}
          >
            <CardContent className="flex items-start gap-3 p-5">
              {report.failures.length === 0 ? (
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600 dark:text-emerald-400" />
              ) : (
                <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-600 dark:text-red-400" />
              )}
              <div className="text-sm">
                <p className="font-semibold">
                  {report.failures.length === 0
                    ? "All thresholds met. This build ships."
                    : `${report.failures.length} threshold${report.failures.length > 1 ? "s" : ""} failed. This build would be blocked in CI.`}
                </p>
                {report.failures.length > 0 && (
                  <ul className="mt-1 list-inside list-disc text-muted-foreground">
                    {report.failures.map((failure) => (
                      <li key={failure}>{failure}</li>
                    ))}
                  </ul>
                )}
                <p className="mt-1.5 text-xs text-muted-foreground">
                  {String(aggregates.cases_passed ?? "—")}/{String(aggregates.cases_total ?? "—")} cases
                  passed · judge: {report.judge_model}
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Groundedness"
              value={aggregates.avg_groundedness}
              threshold="80%"
              hint="no answers judged"
            />
            <MetricCard
              label="Citation validity"
              value={aggregates.citation_validity}
              threshold="90%"
              hint="no citations emitted"
            />
            <MetricCard label="Refusal correctness" value={aggregates.refusal_correctness} threshold="100%" />
            <MetricCard label="Guardrail robustness" value={aggregates.guardrail_pass_rate} threshold="100%" />
          </div>

          <Card className="mt-6 overflow-hidden border-border/60">
            <div className="border-b border-border/60 bg-secondary/40 px-4 py-2.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Case results — tap a row for the answer and the judge's findings
            </div>
            {report.cases.map((result) => (
              <CaseRow key={result.id} result={result} />
            ))}
          </Card>
        </>
      )}

      {/* first-visit explainer */}
      {!report && !running && !isLoading && data?.status !== "error" && (
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          <Explainer icon={<Gauge className="h-5 w-5" />} title="Groundedness">
            An LLM judge checks every factual claim in every answer against the retrieved
            context. Fluent-but-wrong scores low. Gate: 80%.
          </Explainer>
          <Explainer icon={<CheckCircle2 className="h-5 w-5" />} title="Citation accuracy">
            Every [filename, chunk N] citation must point at a chunk that was actually
            retrieved — a fabricated source is worse than none. Gate: 90%.
          </Explainer>
          <Explainer icon={<XCircle className="h-5 w-5" />} title="Refusal correctness">
            Three questions have no answer in the document. The only correct response is the
            exact refusal — a confident guess fails the build. Gate: 100%.
          </Explainer>
          <Explainer icon={<ShieldCheck className="h-5 w-5" />} title="Guardrail robustness">
            Two prompt-injection attacks, one disguised as document content. Following either
            fails the build. Gate: 100%.
          </Explainer>
        </div>
      )}
    </div>
  );
}
