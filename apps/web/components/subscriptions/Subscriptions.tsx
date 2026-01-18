"use client"

import * as React from "react"
import { useState } from "react"
import Link from "next/link"
import {
  CreditCard,
  ChevronLeft,
  ChevronRight,
  ArrowRight,
  Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Subscription } from "./types"
import { formatCurrency, getMonthlyEquivalent } from "./utils"
import { SubscriptionLogo } from "./SubscriptionLogo"
import { ActionMenu } from "./ActionMenu"
import { MobileSubscriptionCard } from "./MobileSubscriptionCard"
import { SubscriptionDetailsDialog } from "./SubscriptionDetailsDialog"
import type { Scope } from "@/types/scope"
import { useApi } from "@/hooks/use-api"
import type { BankingTransaction, ClassificationSummary, SubscriptionAggregated } from "./api-types"
import { NeedsReviewQueue } from "./NeedsReviewQueue"

interface SubscriptionsProps {
  showFlaggedReview?: boolean
  className?: string
  scope?: Scope
}

export function Subscriptions({ showFlaggedReview = true, className, scope }: SubscriptionsProps) {
  const { get, post, isLoaded, isSignedIn } = useApi()
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [needsReview, setNeedsReview] = useState<BankingTransaction[]>([])
  const [isDetecting, setIsDetecting] = useState(false)
  const [isReviewing, setIsReviewing] = useState(false)
  const [currentPage, setCurrentPage] = useState(0)
  const [detailsDialog, setDetailsDialog] = useState<{
    open: boolean
    subscription: Subscription | null
  }>({ open: false, subscription: null })

  const scopeQueryString = React.useMemo(() => {
    if (!scope) return ""
    if (scope.type === "range") {
      const params = new URLSearchParams({
        start_date: scope.startDate,
        end_date: scope.endDate,
      })
      return `?${params.toString()}`
    }
    // statement scope not supported by backend subscription classifier endpoints today
    return ""
  }, [scope])

  const itemsPerPage = 3
  const totalPages = Math.max(1, Math.ceil(subscriptions.length / itemsPerPage))
  const paginatedSubscriptions = subscriptions.slice(
    currentPage * itemsPerPage,
    (currentPage + 1) * itemsPerPage
  )

  React.useEffect(() => {
    // If subscription count changes, keep currentPage within valid bounds.
    const lastPageIndex = Math.max(0, totalPages - 1)
    setCurrentPage((p) => Math.min(p, lastPageIndex))
  }, [totalPages])

  const fetchData = React.useCallback(async () => {
    if (!scope) return
    if (!isLoaded || !isSignedIn) return

    // aggregated supports optional start/end
    const aggregated = await get<SubscriptionAggregated[]>(
      `/api/v1/query/transactions/subscriptions/aggregated${scopeQueryString}`
    )

    // needs-review supports optional start/end
    const needs = await get<BankingTransaction[]>(
      `/api/v1/query/transactions/subscriptions/needs-review${scopeQueryString}`
    )

    // Map aggregated subscriptions into the existing UI model (minimal fields)
    const mapped: Subscription[] = (aggregated || []).map((s) => ({
      id: s.merchant_key,
      name: s.display_name,
      logo: "/logos/af_logo.png",
      amount: Number(s.average_monthly_amount ?? 0),
      frequency: "monthly",
      confidence: s.confidence_avg && s.confidence_avg >= 0.8 ? "high" : s.confidence_avg && s.confidence_avg >= 0.5 ? "medium" : "low",
      confidenceReason: `Based on ${s.transaction_count} transactions across ${s.no_months_subscribed} months`,
      flags: [],
      lastCharges: [],
      category: s.category ?? "Other",
      status: "active",
      statementPeriod: scope.type === "range" ? `${scope.startDate} - ${scope.endDate}` : "Current",
      sourceRef: "",
    }))

    setSubscriptions(mapped)
    setNeedsReview(needs || [])
  }, [get, isLoaded, isSignedIn, scope, scopeQueryString])

  React.useEffect(() => {
    void fetchData()
  }, [fetchData])

  // Calculate summary stats
  const totalMonthly = subscriptions.reduce(
    (sum, s) => sum + getMonthlyEquivalent(s.amount, s.frequency),
    0
  )
  const totalYearly = totalMonthly * 12

  const canDetect = scope?.type === "range"
  const hasAnyData = subscriptions.length > 0 || needsReview.length > 0

  const handleDetect = async () => {
    if (!scope || scope.type !== "range") return
    if (!isLoaded || !isSignedIn) return

    setIsDetecting(true)
    try {
      const params = new URLSearchParams({
        start_date: scope.startDate,
        end_date: scope.endDate,
      })
      await post<ClassificationSummary>(
        `/api/v1/query/transactions/subscriptions/classify?${params.toString()}`,
        {},
      )
      await fetchData()
    } finally {
      setIsDetecting(false)
    }
  }

  const handleReview = async (transactionId: string, decision: "confirmed" | "rejected") => {
    if (!isLoaded || !isSignedIn) return
    setIsReviewing(true)
    try {
      await post<unknown>("/api/v1/query/transactions/subscriptions/review", {
        transaction_id: transactionId,
        decision,
      })
      await fetchData()
    } finally {
      setIsReviewing(false)
    }
  }

  // Action handler
  const handleAction = (action: string, id: string) => {
    console.log(`Action: ${action} on subscription: ${id}`)
    if (action === "copy_cancel") {
      // Toast notification would go here
    }
  }

  return (
    <Card className={cn("w-full border shadow-lg bg-background", className)}>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Subscriptions</CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        {!hasAnyData && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            {isDetecting ? (
              <div className="py-8">
                <Loader2 className="h-10 w-10 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                <div className="rounded-full bg-muted p-4 mb-4">
                  <CreditCard className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold">No subscriptions detected</h3>
                <p className="text-muted-foreground mt-1 max-w-sm">
                  Detect subscriptions from your transactions for the selected date range.
                </p>
                <div className="mt-4">
                  <Button onClick={handleDetect} disabled={!canDetect || isDetecting}>
                    Detect Subscriptions
                  </Button>
                  {!canDetect && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Switch the scope to a date range to run detection.
                    </p>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {/* A. Subscription Summary */}
        {hasAnyData && (
          <section>
          <p className="text-sm text-muted-foreground">Total spending</p>
          <p className="text-5xl font-light tracking-tight">
            <span className="text-2xl align-top font-bold">RM</span>
            <span className="font-bold">{totalMonthly.toFixed(2).split('.')[0]}</span>
            <span className="text-2xl font-bold">.{totalMonthly.toFixed(2).split('.')[1]}</span>
            <span className="text-xl text-muted-foreground font-normal">/m</span>
          </p>
          
          <p className="text-base">
            <span className="text-muted-foreground">You have </span>
            <span className="font-semibold text-foreground">{subscriptions.length} subscriptions</span>
            <span className="text-muted-foreground"> this month</span>
            {needsReview.length > 0 && (
              <>
                <span className="text-muted-foreground"> and </span>
                <span className="font-semibold text-warning">{needsReview.length}</span>
                <span className="text-muted-foreground"> need review.</span>
              </>
            )}
          </p>
          
          <p className="text-base">
            <span className="text-muted-foreground">You will end the year with </span>
            <span className="font-semibold text-success">{formatCurrency(totalYearly)}</span>
          </p>
          </section>
        )}

        {subscriptions.length > 0 && (
          <section>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
            <h2 className="text-lg font-semibold">All Subscriptions ({subscriptions.length})</h2>
          </div>

        {/* Desktop Card View */}
        <div className="hidden md:block space-y-3">
          {subscriptions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <CreditCard className="w-12 h-12 text-muted-foreground mb-4 opacity-50" />
              <p className="text-base font-medium text-muted-foreground">
                No subscriptions detected
              </p>
            </div>
          ) : (
            paginatedSubscriptions.map((subscription) => (
              <div
                key={subscription.id}
                className="py-4 px-4 rounded-lg border cursor-pointer transition-colors hover:bg-muted/20"
                role="button"
                tabIndex={0}
                onClick={() => setDetailsDialog({ open: true, subscription })}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault()
                    setDetailsDialog({ open: true, subscription })
                  }
                }}
              >
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <SubscriptionLogo
                      name={subscription.name}
                      logo={subscription.logo}
                    />
                    <div className="min-w-0">
                      <p className="font-medium truncate">{subscription.name}</p>
                      <p className="text-xs text-muted-foreground truncate">
                        {subscription.category}
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="font-medium">
                      {formatCurrency(subscription.amount)}
                    </p>
                    <p className="text-xs text-muted-foreground capitalize">
                      {subscription.frequency}
                    </p>
                  </div>

                  <div className="flex items-center gap-1">
                    <ActionMenu
                      subscription={subscription}
                      onAction={handleAction}
                    />
                  </div>
                </div>
              </div>
            ))
          )}

          {subscriptions.length > 0 && totalPages > 1 && (
            <div className="flex items-center justify-center gap-4 pt-2">
              <Button
                variant="outline"
                size="icon"
                disabled={currentPage === 0}
                onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
                aria-label="Previous page"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-sm text-muted-foreground">
                {currentPage + 1} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="icon"
                disabled={currentPage >= totalPages - 1}
                onClick={() =>
                  setCurrentPage((p) => Math.min(totalPages - 1, p + 1))
                }
                aria-label="Next page"
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          )}

        </div>

        {/* Mobile Card View */}
        <div className="md:hidden space-y-3">
          {subscriptions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <CreditCard className="w-12 h-12 text-muted-foreground mb-4 opacity-50" />
              <p className="text-base font-medium text-muted-foreground">
                No subscriptions detected
              </p>
            </div>
          ) : (
            <>
              {paginatedSubscriptions.map((subscription) => (
                <MobileSubscriptionCard
                  key={subscription.id}
                  subscription={subscription}
                  onAction={handleAction}
                  onOpenDetails={() => setDetailsDialog({ open: true, subscription })}
                />
              ))}
            </>
          )}

          {subscriptions.length > 0 && totalPages > 1 && (
            <div className="flex items-center justify-center gap-4 pt-1">
              <Button
                variant="outline"
                size="icon"
                disabled={currentPage === 0}
                onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
                aria-label="Previous page"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-sm text-muted-foreground">
                {currentPage + 1} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="icon"
                disabled={currentPage >= totalPages - 1}
                onClick={() => setCurrentPage((p) => Math.min(totalPages - 1, p + 1))}
                aria-label="Next page"
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          )}
        </div>
      </section>
        )}

        {/* Needs review section */}
        {showFlaggedReview && needsReview.length > 0 && (
          <NeedsReviewQueue
            items={needsReview}
            isWorking={isReviewing}
            onConfirm={(id) => handleReview(id, "confirmed")}
            onReject={(id) => handleReview(id, "rejected")}
            onSkip={() => {}}
          />
        )}

      </CardContent>

      {/* Subscription Details Modal */}
      <SubscriptionDetailsDialog
        subscription={detailsDialog.subscription}
        open={detailsDialog.open}
        onOpenChange={(open) =>
          setDetailsDialog((prev) => ({ ...prev, open }))
        }
        onAction={handleAction}
      />
    </Card>
  )
}
