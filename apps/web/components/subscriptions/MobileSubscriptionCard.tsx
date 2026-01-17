"use client"

import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { Subscription } from "./types"
import { SubscriptionLogo } from "./SubscriptionLogo"
import { ActionMenu } from "./ActionMenu"
import { formatCurrency } from "./utils"

export function MobileSubscriptionCard({
  subscription,
  onAction,
  onOpenDetails,
}: {
  subscription: Subscription
  onAction: (action: string, id: string) => void
  onOpenDetails: () => void
}) {
  return (
    <Card
      className="transition-all cursor-pointer"
      role="button"
      tabIndex={0}
      onClick={onOpenDetails}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          onOpenDetails()
        }
      }}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <SubscriptionLogo name={subscription.name} logo={subscription.logo} />
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-medium truncate">{subscription.name}</h3>
                <p className="text-sm text-muted-foreground">{subscription.category}</p>
              </div>
              <ActionMenu subscription={subscription} onAction={onAction} />
            </div>

            <div className="mt-3 flex items-center gap-2 flex-wrap">
              <span className="font-semibold">{formatCurrency(subscription.amount)}</span>
              <span className="text-xs text-muted-foreground capitalize">
                /{subscription.frequency.replace("ly", "")}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
