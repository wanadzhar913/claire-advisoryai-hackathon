"use client"

import { Check, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { Subscription } from "./types"
import { SubscriptionLogo } from "./SubscriptionLogo"
import { formatCurrency } from "./utils"

export function SubscriptionDetailsDialog({
  subscription,
  open,
  onOpenChange,
  onAction,
}: {
  subscription: Subscription | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onAction: (action: string, id: string) => void
}) {
  if (!subscription) return null

  const totalCharges = subscription.lastCharges.reduce((sum, c) => sum + c.amount, 0)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl overflow-y-auto max-h-[85vh]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <SubscriptionLogo name={subscription.name} logo={subscription.logo} />
            <div>
              <DialogTitle>{subscription.name}</DialogTitle>
              <DialogDescription>{subscription.category}</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-6 py-2">
          {/* Summary */}
          <div>
            <p className="text-xs text-muted-foreground mb-1">Amount</p>
            <p className="text-3xl font-semibold">{formatCurrency(subscription.amount)}</p>
            <p className="text-xs text-muted-foreground capitalize mt-1">{subscription.frequency}</p>
          </div>

          <Separator />

          {/* Statement Info */}
          <div>
            <h4 className="text-sm font-medium mb-2">Statement Details</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Period</span>
                <span>{subscription.statementPeriod}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Source</span>
                <span>{subscription.sourceRef}</span>
              </div>
            </div>
          </div>

          <Separator />

          {/* Recent Charges */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium">Recent Charges</h4>
              <span className="text-xs text-muted-foreground">
                Total: {formatCurrency(totalCharges)}
              </span>
            </div>
            <div className="space-y-2">
              {subscription.lastCharges.map((charge, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded-lg bg-muted/30 text-sm"
                >
                  <div>
                    <p className="font-medium">{charge.description}</p>
                    <p className="text-xs text-muted-foreground">{charge.date}</p>
                  </div>
                  <span className="font-medium">{formatCurrency(charge.amount)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-col sm:items-stretch">
          <Button
            className="w-full"
            variant="outline"
            onClick={() => onAction("keep", subscription.id)}
          >
            <Check className="w-4 h-4 mr-2" />
            Keep Subscription
          </Button>
          <Button
            className="w-full"
            variant="outline"
            onClick={() => onAction("cancel", subscription.id)}
          >
            <X className="w-4 h-4 mr-2" />
            Mark for Cancellation
          </Button>
          <Button
            className="w-full"
            variant="ghost"
            onClick={() => onAction("not_subscription", subscription.id)}
          >
            Not a Subscription
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
