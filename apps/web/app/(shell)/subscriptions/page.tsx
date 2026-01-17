"use client"

import { Subscriptions } from "@/components/subscriptions"

export default function SubscriptionsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Subscriptions</h1>
        <p className="text-muted-foreground mt-2">
          Manage your active subscriptions and recurring payments
        </p>
      </div>

      <Subscriptions />
    </div>
  )
}
