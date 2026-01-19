"use client";

import * as React from "react";
import { Sparkles, Target, CheckCircle2, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { useApi } from "@/hooks/use-api";
import { useScope } from "@/contexts/ScopeContext";
import {
  formatRM,
  type EarnExtraPlan,
  type PlanActionProgress,
} from "@/lib/earn-extra-data";

export interface EarnExtraProps {
  className?: string;
}

export function EarnExtra({ className }: EarnExtraProps) {
  const { get, post, patch, isLoaded, isSignedIn } = useApi();
  const { scope } = useScope();

  const [plans, setPlans] = React.useState<EarnExtraPlan[]>([]);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);
  const [generating, setGenerating] = React.useState<boolean>(false);
  const [saving, setSaving] = React.useState<boolean>(false);

  const activePlan = plans.find((plan) => plan.status === "active") || null;
  const generatedPlans = plans.filter((plan) => plan.status === "generated");

  const [savedSoFar, setSavedSoFar] = React.useState<string>("");
  const [actionsProgress, setActionsProgress] = React.useState<
    PlanActionProgress[]
  >([]);

  const normalizePlan = React.useCallback(
    (plan: EarnExtraPlan): EarnExtraPlan => {
      return {
        ...plan,
        target_amount: Number(plan.target_amount),
        expected_amount:
          plan.expected_amount != null
            ? Number(plan.expected_amount)
            : plan.expected_amount,
        saved_so_far: Number(plan.saved_so_far),
      };
    },
    [],
  );

  const normalizePlans = React.useCallback(
    (items: EarnExtraPlan[]) => items.map((plan) => normalizePlan(plan)),
    [normalizePlan],
  );

  React.useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setPlans([]);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;

    async function loadPlans() {
      setLoading(true);
      setError(null);
      try {
        const result = await get<EarnExtraPlan[]>(`/api/v1/earn-extra/plans`);
        if (cancelled) return;
        setPlans(normalizePlans(result));
      } catch (e) {
        if (cancelled) return;
        const message = e instanceof Error ? e.message : "Failed to load plans";
        setError(message);
        setPlans([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadPlans();

    return () => {
      cancelled = true;
    };
  }, [get, isLoaded, isSignedIn]);

  React.useEffect(() => {
    if (!activePlan) {
      setSavedSoFar("");
      setActionsProgress([]);
      return;
    }
    setSavedSoFar(activePlan.saved_so_far?.toString() ?? "0");
    setActionsProgress(activePlan.actions_progress ?? []);
  }, [activePlan]);

  const handleGenerate = async () => {
    if (!isSignedIn) return;
    setGenerating(true);
    setError(null);
    try {
      const payload: { file_id?: string } = {};
      if (scope?.type === "statement") {
        payload.file_id = scope.fileId;
      }
      const result = await post<EarnExtraPlan[]>(
        "/api/v1/earn-extra/plans/generate",
        payload,
      );
      setPlans(normalizePlans(result));
    } catch (e) {
      const message =
        e instanceof Error ? e.message : "Failed to generate plans";
      setError(message);
    } finally {
      setGenerating(false);
    }
  };

  const handleActivate = async (planId: string) => {
    setSaving(true);
    setError(null);
    try {
      const updated = await post<EarnExtraPlan>(
        `/api/v1/earn-extra/plans/${planId}/activate`,
        {},
      );
      const normalized = normalizePlan(updated);
      setPlans((prev) =>
        prev.map((plan) =>
          plan.id === normalized.id
            ? normalized
            : plan.status === "active"
              ? { ...plan, status: "archived" }
              : plan,
        ),
      );
    } catch (e) {
      const message =
        e instanceof Error ? e.message : "Failed to activate plan";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleAction = (index: number) => {
    setActionsProgress((prev) => {
      const next = [...prev];
      const current = next[index] || { is_done: false };
      next[index] = { ...current, is_done: !current.is_done };
      return next;
    });
  };

  const handleSaveProgress = async () => {
    if (!activePlan) return;
    const numericSaved = Number(savedSoFar);
    if (!Number.isFinite(numericSaved) || numericSaved < 0) {
      setError("Saved so far must be a non-negative number");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const payload = {
        saved_so_far: numericSaved,
        actions_progress: actionsProgress,
      };
      const updated = await patch<EarnExtraPlan>(
        `/api/v1/earn-extra/plans/${activePlan.id}`,
        payload,
      );
      const normalized = normalizePlan(updated);
      setPlans((prev) =>
        prev.map((plan) => (plan.id === normalized.id ? normalized : plan)),
      );
    } catch (e) {
      const message =
        e instanceof Error ? e.message : "Failed to update progress";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleComplete = async () => {
    if (!activePlan) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await post<EarnExtraPlan>(
        `/api/v1/earn-extra/plans/${activePlan.id}/complete`,
        {},
      );
      const normalized = normalizePlan(updated);
      setPlans((prev) =>
        prev.map((plan) => (plan.id === normalized.id ? normalized : plan)),
      );
    } catch (e) {
      const message =
        e instanceof Error ? e.message : "Failed to complete plan";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const progressPct = activePlan
    ? Math.round((activePlan.saved_so_far / activePlan.target_amount) * 100)
    : 0;

  return (
    <Card className={cn("w-full border shadow-lg bg-background", className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="text-lg font-semibold">
              Wanna earn RM500 extra? Here’s how:
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              {loading
                ? "Loading plans…"
                : activePlan
                  ? "Tracking your active plan"
                  : generatedPlans.length > 0
                    ? "Pick a plan to get started"
                    : "Generate a plan based on your spending"}
            </p>
            {(loading || generating) && (
              <p className="text-xs text-muted-foreground">This may take a few minutes...</p>
            )}
          </div>
          {activePlan ? (
            <Badge variant="outline" className="shrink-0">
              Active
            </Badge>
          ) : (
            <Badge variant="secondary" className="shrink-0">
              New
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-2">
        {!!error && <p className="text-xs text-destructive">{error}</p>}

        {!loading && !isSignedIn && (
          <p className="text-sm">
            Sign in to generate your personalized plans.
          </p>
        )}

        {!loading &&
          isSignedIn &&
          !activePlan &&
          generatedPlans.length === 0 && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Get three actionable plans based on your recent transactions.
              </p>
              <Button
                className="w-full"
                onClick={handleGenerate}
                disabled={generating}
              >
                {generating && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                {generating ? "Generating plans…" : "Generate plans"}
              </Button>
            </div>
          )}

        {!loading && isSignedIn && !activePlan && generatedPlans.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm font-medium">Pick a plan</p>
            <div className="space-y-3">
              {generatedPlans.map((plan) => (
                <div
                  key={plan.id}
                  className="p-3 rounded-lg bg-muted/50 space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-muted-foreground shrink-0" />
                        <p className="text-sm font-medium truncate">
                          {plan.title}
                        </p>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {plan.summary}
                      </p>
                    </div>
                    <Badge variant="outline" className="shrink-0">
                      Target: {formatRM(plan.target_amount)}
                    </Badge>
                  </div>

                  <ul className="space-y-1 text-xs text-muted-foreground">
                    {plan.actions.map((action, index) => (
                      <li
                        key={`${plan.id}-${index}`}
                        className="flex items-center gap-2"
                      >
                        <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60" />
                        <span className="truncate">{action.label}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    className="w-full"
                    onClick={() => handleActivate(plan.id)}
                    disabled={saving}
                  >
                    {saving ? "Activating…" : "Activate plan"}
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {!loading && isSignedIn && activePlan && (
          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-muted/50 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-muted-foreground shrink-0" />
                    <p className="text-sm font-medium truncate">
                      {activePlan.title}
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {activePlan.summary}
                  </p>
                </div>
                <Badge variant="outline" className="shrink-0">
                  {formatRM(activePlan.target_amount)} ·{" "}
                  {activePlan.timeframe_days} days
                </Badge>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">Progress</p>
                  <p className="text-xs font-medium">
                    {Math.min(100, Math.max(0, progressPct))}%
                  </p>
                </div>
                <div className="h-2 w-full rounded-full bg-background">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{
                      width: `${Math.min(100, Math.max(0, progressPct))}%`,
                    }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  {formatRM(activePlan.saved_so_far)} /{" "}
                  {formatRM(activePlan.target_amount)}
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-muted-foreground">
                  Saved so far (RM)
                </label>
                <Input
                  type="number"
                  min={0}
                  step={1}
                  value={savedSoFar}
                  onChange={(event) => setSavedSoFar(event.target.value)}
                />
              </div>

              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">
                  Action checklist
                </p>
                <div className="space-y-2">
                  {activePlan.actions.map((action, index) => (
                    <label
                      key={`${activePlan.id}-action-${index}`}
                      className="flex items-start gap-2 text-sm"
                    >
                      <Checkbox
                        checked={actionsProgress[index]?.is_done ?? false}
                        onCheckedChange={() => handleToggleAction(index)}
                      />
                      <span className="text-xs text-muted-foreground leading-5">
                        {action.label}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="pt-2 flex flex-col gap-2">
        {activePlan ? (
          <>
            <Button
              className="w-full"
              onClick={handleSaveProgress}
              disabled={saving}
            >
              {saving ? "Saving…" : "Save progress"}
            </Button>
            <Button
              variant="outline"
              className="w-full"
              onClick={handleComplete}
              disabled={saving}
            >
              <CheckCircle2 className="mr-2 h-4 w-4" /> Mark completed
            </Button>
          </>
        ) : null}
      </CardFooter>
    </Card>
  );
}
