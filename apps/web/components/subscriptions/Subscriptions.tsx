"use client"

import * as React from "react"
import { useState } from "react"
import {
  CreditCard,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { Subscription } from "./types"
import { mockSubscriptions } from "./mock-data"
import { formatCurrency, getMonthlyEquivalent } from "./utils"
import { SubscriptionLogo } from "./SubscriptionLogo"
import { ActionMenu } from "./ActionMenu"
import { MobileSubscriptionCard } from "./MobileSubscriptionCard"
import { SubscriptionDetailsDialog } from "./SubscriptionDetailsDialog"
import { FlaggedItemsReview } from "./FlaggedItemsReview"

export function Subscriptions() {
  const [subscriptions, setSubscriptions] = useState(mockSubscriptions)
  const [reviewedFlaggedIds, setReviewedFlaggedIds] = useState<Set<string>>(new Set())
  const [currentPage, setCurrentPage] = useState(0)
  const [detailsDialog, setDetailsDialog] = useState<{
    open: boolean
    subscription: Subscription | null
  }>({ open: false, subscription: null })

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

  // Calculate summary stats
  const totalMonthly = subscriptions.reduce(
    (sum, s) => sum + getMonthlyEquivalent(s.amount, s.frequency),
    0
  )
  const totalYearly = totalMonthly * 12
  const flaggedSubscriptions = subscriptions.filter((s) => s.flags.length > 0)
  const unreviewedFlagged = flaggedSubscriptions.filter((s) => !reviewedFlaggedIds.has(s.id))
  const flaggedCount = flaggedSubscriptions.length
  const currentFlagged = unreviewedFlagged[0] // Show one at a time
  const reviewedCount = reviewedFlaggedIds.size

  // Handle flagged subscription action - mark as reviewed and move to next
  const handleFlaggedAction = (action: "subscription" | "not_subscription" | "dont_know", id: string) => {
    console.log(`Flagged action: ${action} on subscription: ${id}`)
    
    // Mark as reviewed
    setReviewedFlaggedIds((prev) => new Set([...prev, id]))
    
    // Update subscription status
    setSubscriptions((prev) =>
      prev.map((s) =>
        s.id === id
          ? {
              ...s,
              status: action === "subscription" ? "active" : action === "not_subscription" ? "not_subscription" : s.status,
              // Clear flags if user confirmed it's a subscription or not
              flags: action === "dont_know" ? s.flags : [],
            }
          : s
      )
    )
  }

  // Action handler
  const handleAction = (action: string, id: string) => {
    console.log(`Action: ${action} on subscription: ${id}`)
    // In a real app, this would update state/call API
    if (action === "copy_cancel") {
      // Toast notification would go here
    }
  }

  return (
    <div className="space-y-6">
      {/* A. Subscription Summary */}
      <section className="space-y-4">
        <p className="text-sm text-muted-foreground">Total spending</p>
        <p className="text-5xl font-light tracking-tight">
          <span className="text-2xl align-top font-bold">$</span>
          <span className="font-bold">{totalMonthly.toFixed(2).split('.')[0]}</span>
          <span className="text-2xl font-bold">.{totalMonthly.toFixed(2).split('.')[1]}</span>
          <span className="text-xl text-muted-foreground font-normal">/m</span>
        </p>
        
        <p className="text-base">
          <span className="text-muted-foreground">You have </span>
          <span className="font-semibold text-foreground">{subscriptions.length} subscriptions</span>
          <span className="text-muted-foreground"> this month</span>
          {flaggedCount > 0 && (
            <>
              <span className="text-muted-foreground"> and </span>
              <span className="font-semibold text-amber-600">{flaggedCount}</span>
              <span className="text-muted-foreground"> need review.</span>
            </>
          )}
        </p>
        
        <p className="text-base">
          <span className="text-muted-foreground">You will end the month with </span>
          <span className="font-semibold text-emerald-600">{formatCurrency(totalYearly)}</span>
        </p>
      </section>

      {/* B. Subscription List */}
      <section>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
          <h2 className="text-lg font-semibold">All Subscriptions ({subscriptions.length})</h2>
        </div>

        {/* Desktop Card View */}
        <div className="hidden md:block">
          <Card>
            <CardContent className="space-y-3">
              {subscriptions.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <CreditCard className="w-12 h-12 text-muted-foreground mb-4 opacity-50" />
                  <p className="text-base font-medium text-muted-foreground">
                    No subscriptions detected
                  </p>
                </div>
              ) : (
                paginatedSubscriptions.map((subscription) => (
                  <Card
                    key={subscription.id}
                    className="py-4 shadow-none cursor-pointer transition-colors hover:bg-muted/20"
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
                    <CardContent className="px-4">
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
                    </CardContent>
                  </Card>
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
            </CardContent>

            {/* Flagged Subscriptions Section - One at a time */}
            {subscriptions.length > 0 && (
              <FlaggedItemsReview
                flaggedSubscriptions={flaggedSubscriptions}
                currentFlagged={currentFlagged}
                reviewedCount={reviewedCount}
                flaggedCount={flaggedCount}
                onAction={handleFlaggedAction}
                isMobile={false}
              />
            )}
          </Card>
        </div>

        {/* Mobile Card View */}
        <div className="md:hidden space-y-3">
          {subscriptions.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                <CreditCard className="w-12 h-12 text-muted-foreground mb-4 opacity-50" />
                <p className="text-base font-medium text-muted-foreground">
                  No subscriptions detected
                </p>
              </CardContent>
            </Card>
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
          
          {/* Flagged Subscriptions Section for Mobile - One at a time */}
          {flaggedCount > 0 && (
            <Card>
              <CardContent className="pt-6">
                <FlaggedItemsReview
                  flaggedSubscriptions={flaggedSubscriptions}
                  currentFlagged={currentFlagged}
                  reviewedCount={reviewedCount}
                  flaggedCount={flaggedCount}
                  onAction={handleFlaggedAction}
                  isMobile={true}
                />
              </CardContent>
            </Card>
          )}
        </div>
      </section>

      {/* Subscription Details Modal */}
      <SubscriptionDetailsDialog
        subscription={detailsDialog.subscription}
        open={detailsDialog.open}
        onOpenChange={(open) =>
          setDetailsDialog((prev) => ({ ...prev, open }))
        }
        onAction={handleAction}
      />
    </div>
  )
}
