"use client"

import * as React from "react"
import { AlertCircle, Check, HelpCircle, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { SubscriptionLogo } from "./SubscriptionLogo"
import type { BankingTransaction } from "./api-types"
import { formatCurrency } from "./utils"

type Props = {
  items: BankingTransaction[]
  onConfirm: (transactionId: string) => void | Promise<void>
  onReject: (transactionId: string) => void | Promise<void>
  onSkip?: (transactionId: string) => void
  isWorking?: boolean
}

export function NeedsReviewQueue({
  items,
  onConfirm,
  onReject,
  onSkip,
  isWorking = false,
}: Props) {
  if (!items.length) return null

  const current = items[0]
  const reviewedCount = 0
  const total = items.length

  const displayName =
    current.subscription_name ||
    current.subscription_merchant_key ||
    current.merchant_name ||
    "Unknown"

  return (
    <div className="border-t p-6">
      <div className="flex items-center gap-2 mb-4">
        <AlertCircle className="w-5 h-5 text-warning" />
        <h3 className="text-base font-semibold">Needs review</h3>
        <Badge variant="outline" className="ml-auto">
          {reviewedCount}/{total}
        </Badge>
      </div>

      <p className="text-sm text-muted-foreground mb-4">Is this a subscription?</p>

      <Card className="border-warning/30 bg-warning/10">
        <CardContent className="p-4">
          <div className="flex items-start gap-3 mb-4">
            <SubscriptionLogo name={displayName} logo="/logos/af_logo.png" />
            <div className="flex-1 min-w-0">
              <h4 className="font-medium truncate">{displayName}</h4>
              <p className="text-sm text-muted-foreground mt-1 truncate">
                {current.description}
              </p>
              <p className="text-sm font-semibold mt-2">
                {formatCurrency(Number(current.amount))}
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              disabled={isWorking}
              onClick={() => onConfirm(current.id)}
            >
              <Check className="w-4 h-4 mr-2" />
              Subscription
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              disabled={isWorking}
              onClick={() => onReject(current.id)}
            >
              <X className="w-4 h-4 mr-2" />
              Not a subscription
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              disabled={isWorking}
              onClick={() => onSkip?.(current.id)}
            >
              <HelpCircle className="w-4 h-4 mr-2" />
              Don't know
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

