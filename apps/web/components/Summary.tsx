"use client";

import * as React from "react";
import {
  X,
  Coffee,
  Utensils,
  ArrowRightLeft,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Lightbulb,
  ShoppingCart,
  Car,
  Home,
  Gamepad,
  Heart,
  GraduationCap,
  Zap,
  CreditCard,
  Repeat,
  Calendar,
  PiggyBank,
  Target,
  Shield,
  Wallet,
  RefreshCw,
  Loader2,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/use-api";
import { useScope } from "@/contexts/ScopeContext";
import type { Scope } from "@/types/scope";

// Icon mapping for dynamic icon rendering
const iconMap: Record<string, React.ElementType> = {
  Coffee,
  Utensils,
  ArrowRightLeft,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Lightbulb,
  ShoppingCart,
  Car,
  Home,
  Gamepad,
  Heart,
  GraduationCap,
  Zap,
  CreditCard,
  Repeat,
  Calendar,
  PiggyBank,
  Target,
  Shield,
  Wallet,
};

// Types for API response
interface Insight {
  id: string;
  user_id: number;
  file_id: string | null;
  insight_type: "pattern" | "alert" | "recommendation";
  title: string;
  description: string;
  icon: string;
  severity: "info" | "warning" | "critical" | null;
  metadata: Record<string, unknown> | null;
  created_at: string | null;
}

interface InsightsResponse {
  insights: Insight[];
  patterns: Insight[];
  alerts: Insight[];
  recommendations: Insight[];
  count: number;
}

interface SummaryProps {
  onClose?: () => void;
  onViewDetails?: () => void;
  className?: string;
  scope?: Scope;
}

// Helper function to build query string from scope
function buildScopeQuery(scope?: Scope): string {
  if (!scope) return "";

  const params = new URLSearchParams();
  if (scope.type === "statement") {
    params.set("file_id", scope.fileId);
  } else if (scope.type === "range") {
    params.set("start_date", scope.startDate);
    params.set("end_date", scope.endDate);
  }

  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
}

export function Summary({
  onClose,
  onViewDetails,
  className,
  scope,
}: SummaryProps) {
  const { get, post, isSignedIn, isLoaded } = useApi();
  const { files, filesLoading } = useScope();
  const [data, setData] = React.useState<InsightsResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [refreshing, setRefreshing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const isProcessing = React.useMemo(() => {
    if (!scope || filesLoading) return false;
    if (scope.type !== "statement") return false;
    const file = files.find((f) => f.file_id === scope.fileId);
    return file?.status === "processing";
  }, [scope, files, filesLoading]);

  const wasProcessingRef = React.useRef<boolean | null>(null);

  // Fetch insights on mount or when scope changes
  const fetchInsights = React.useCallback(async () => {
    if (!isSignedIn) return;

    try {
      setError(null);
      setLoading(true);
      const queryString = buildScopeQuery(scope);
      const response = await get<InsightsResponse>(
        `/api/v1/insights${queryString}`,
      );
      setData(response);
    } catch (err) {
      console.error("Failed to fetch insights:", err);
      setError("Failed to load insights");
    } finally {
      setLoading(false);
    }
  }, [get, isSignedIn, scope]);

  // Trigger new analysis
  const handleRefresh = async () => {
    if (!isSignedIn || refreshing) return;

    setRefreshing(true);
    try {
      await post("/api/v1/insights/analyze", {});
      await fetchInsights();
    } catch (err) {
      console.error("Failed to analyze transactions:", err);
      setError("Failed to analyze transactions");
    } finally {
      setRefreshing(false);
    }
  };

  React.useEffect(() => {
    if (isLoaded && isSignedIn) {
      fetchInsights();
    } else if (isLoaded && !isSignedIn) {
      setLoading(false);
    }
  }, [isLoaded, isSignedIn, fetchInsights]);

  React.useEffect(() => {
    if (!isLoaded || !isSignedIn) return;

    const wasProcessing = wasProcessingRef.current;
    if (wasProcessing === true && !isProcessing) {
      fetchInsights();
    }
    wasProcessingRef.current = isProcessing;
  }, [isProcessing, isLoaded, isSignedIn, fetchInsights]);

  // Loading state
  if (loading) {
    return (
      <Card className={cn("w-full border shadow-lg bg-background", className)}>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-semibold">
              Financial Summary
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-5 pt-2">
          <div className="space-y-3">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
          <div className="space-y-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Not signed in state
  if (!isSignedIn) {
    return (
      <Card className={cn("w-full border shadow-lg bg-background", className)}>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-semibold">
            Financial Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Sign in to view your financial insights.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error && !data) {
    return (
      <Card className={cn("w-full border shadow-lg bg-background", className)}>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-semibold">
            Financial Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">{error}</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={fetchInsights}
          >
            Try Again
          </Button>
        </CardContent>
      </Card>
    );
  }

  const patterns = data?.patterns || [];
  const alerts = data?.alerts || [];
  const recommendations = data?.recommendations || [];

  // UI caps (keep dashboard summary scannable regardless of backend volume)
  const cappedPatterns = patterns.slice(0, 3);
  const cappedAlerts = alerts.slice(0, 1);
  const cappedRecommendations = recommendations.slice(0, 1);
  const hasNoData =
    cappedPatterns.length === 0 &&
    cappedAlerts.length === 0 &&
    cappedRecommendations.length === 0;

  return (
    <Card className={cn("w-full border shadow-lg bg-background", className)}>
      {/* Header */}
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">
            Financial Summary
          </CardTitle>
          <Link
            href="/advice"
            className="flex items-center gap-1 text-sm text-primary underline hover:opacity-80 transition-opacity"
          >
            Chat with your finance
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </CardHeader>

      <CardContent className="space-y-5 pt-2">
        {isProcessing && (
          <div className="flex items-center gap-2 rounded-md border border-amber-200/50 bg-amber-50/50 px-3 py-2 text-sm text-amber-700 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-200">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            <span>Processing statement… insights will appear shortly.</span>
          </div>
        )}
        {/* Empty state */}
        {hasNoData && (
          <div className="text-center py-6">
            <Lightbulb className="w-10 h-10 mx-auto text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">
              No insights yet. Upload a bank statement to get started.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              {refreshing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                "Analyze Transactions"
              )}
            </Button>
          </div>
        )}

        {/* Spending Patterns */}
        {cappedPatterns.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb className="w-4 h-4 text-amber-500" />
              <h3 className="text-sm font-medium">Spending Insights</h3>
            </div>
            <div className="space-y-3">
              {cappedPatterns.map((insight) => {
                const IconComponent = iconMap[insight.icon] || Lightbulb;
                return (
                  <div
                    key={insight.id}
                    className="flex items-start gap-3 p-3 rounded-lg bg-muted/50"
                  >
                    <div className="p-2 rounded-lg bg-background shrink-0">
                      <IconComponent className="w-4 h-4 text-muted-foreground" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{insight.title}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {insight.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Alerts */}
        {cappedAlerts.length > 0 && (
          <section>
            <div className="space-y-2">
              {cappedAlerts.map((alert) => {
                const IconComponent = iconMap[alert.icon] || AlertTriangle;
                return (
                  <div
                    key={alert.id}
                    className="flex items-center gap-2 text-sm"
                  >
                    <IconComponent
                      className={cn(
                        "w-4 h-4 shrink-0",
                        alert.severity === "critical"
                          ? "text-destructive"
                          : alert.severity === "warning"
                            ? "text-amber-500"
                            : "text-blue-500",
                      )}
                    />
                    <div className="min-w-0">
                      <span className="font-medium">{alert.title}: </span>
                      <span className="text-muted-foreground">
                        {alert.description}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Recommendations */}
        {cappedRecommendations.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-emerald-500" />
              <h3 className="text-sm font-medium">Recommendations</h3>
            </div>
            <div className="space-y-3">
              {cappedRecommendations.map((rec) => {
                const IconComponent = iconMap[rec.icon] || Lightbulb;
                return (
                  <div
                    key={rec.id}
                    className="flex items-start gap-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20"
                  >
                    <div className="p-2 rounded-lg bg-emerald-500/20 shrink-0">
                      <IconComponent className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{rec.title}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {rec.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </CardContent>
    </Card>
  );
}
