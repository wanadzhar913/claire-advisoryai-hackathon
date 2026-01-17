"use client"

import { AlertCircle, Check, HelpCircle, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Subscription } from "./types"
import { SubscriptionLogo } from "./SubscriptionLogo"
import { formatCurrency, getMonthlyEquivalent } from "./utils"

interface FlaggedItemsReviewProps {
  flaggedSubscriptions: Subscription[]
  currentFlagged: Subscription | undefined
  reviewedCount: number
  flaggedCount: number
  onAction: (action: "subscription" | "not_subscription" | "dont_know", id: string) => void
  isMobile?: boolean
}

export function FlaggedItemsReview({
  flaggedSubscriptions,
  currentFlagged,
  reviewedCount,
  flaggedCount,
  onAction,
  isMobile = false,
}: FlaggedItemsReviewProps) {
  if (flaggedCount === 0) return null

  const potentialSavings = flaggedSubscriptions.reduce(
    (sum, s) => sum + getMonthlyEquivalent(s.amount, s.frequency),
    0
  )

  return (
      <div className={isMobile ? "" : "border-t p-6"}>
      <div className="flex items-center gap-2 mb-4">
        <AlertCircle className="w-5 h-5 text-warning" />
        <h3 className="text-base font-semibold">Review Flagged Items</h3>
        <Badge variant="outline" className="ml-auto">
          {reviewedCount}/{flaggedCount}{isMobile ? "" : " reviewed"}
        </Badge>
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 bg-muted rounded-full mb-4 overflow-hidden">
        <div
          className="h-full bg-warning transition-all duration-300"
          style={{ width: `${(reviewedCount / flaggedCount) * 100}%` }}
        />
      </div>

      {currentFlagged ? (
        <>
          <p className="text-sm text-muted-foreground mb-4">
            Is this a subscription?
          </p>
          <Card className="border-warning/30 bg-warning/10">
            <CardContent className="p-4">
              <div className={`flex items-start gap-3 ${isMobile ? "mb-4" : ""}`}>
                <SubscriptionLogo
                  name={currentFlagged.name}
                  logo={currentFlagged.logo}
                />
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium">{currentFlagged.name}</h4>
                  <p className="text-sm text-muted-foreground mt-1">
                    {currentFlagged.lastCharges[0]?.description || currentFlagged.category}
                  </p>
                  <p className="text-sm font-semibold mt-2">
                    {formatCurrency(currentFlagged.amount)}/{currentFlagged.frequency.replace("ly", "")}
                  </p>
                </div>
              </div>
              <div className={`flex gap-2 ${isMobile ? "flex-col" : "mt-4"}`}>
                <Button
                  variant="outline"
                  size="sm"
                  className={isMobile ? "w-full" : "flex-1"}
                  onClick={() => onAction("subscription", currentFlagged.id)}
                >
                  <Check className="w-4 h-4 mr-2" />
                  Subscription
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className={isMobile ? "w-full" : "flex-1"}
                  onClick={() => onAction("not_subscription", currentFlagged.id)}
                >
                  <X className="w-4 h-4 mr-2" />
                  Not a subscription
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className={isMobile ? "w-full" : "flex-1"}
                  onClick={() => onAction("dont_know", currentFlagged.id)}
                >
                  <HelpCircle className="w-4 h-4 mr-2" />
                  Don't know
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        <div className="text-center py-6">
          <Check className="w-10 h-10 text-success mx-auto mb-3" />
          <p className="text-sm font-medium text-success-foreground">
            All flagged items reviewed!
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            You've reviewed all {flaggedCount} flagged subscriptions.
          </p>
        </div>
      )}

      <div className="mt-4 p-4 rounded-lg bg-success/10 border border-success/30">
        <p className="text-sm font-medium text-success-foreground">
          Potential Savings
        </p>
        <p className="text-xs text-success mt-1">
          Review flagged subscriptions to identify potential savings of up to{" "}
          <span className="font-semibold">
            {formatCurrency(potentialSavings)}
          </span>{" "}
          per month.
        </p>
      </div>
    </div>
  )
}
