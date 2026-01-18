"use client"

import { CreditCard } from "lucide-react"
import { Subscriptions } from "@/components/subscriptions"
import { ScopeSelector } from "@/components/ScopeSelector"
import { useScope } from "@/contexts/ScopeContext"

export default function SubscriptionsPage() {
  const { scope, hasFiles, filesLoading } = useScope()

  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Subscriptions</h1>
          <p className="text-muted-foreground mt-2">
            Manage your active subscriptions and recurring payments
          </p>
        </div>
        
        {/* Scope Selector */}
        <ScopeSelector />
      </div>

      {/* Show empty state if no files */}
      {!filesLoading && !hasFiles && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="rounded-full bg-muted p-4 mb-4">
            <CreditCard className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">No statements uploaded</h3>
          <p className="text-muted-foreground mt-1 max-w-sm">
            Upload a bank statement to detect your subscriptions.
          </p>
        </div>
      )}

      {/* Subscriptions content - only show when we have files and a scope */}
      {hasFiles && scope && (
        <Subscriptions scope={scope} />
      )}
    </div>
  )
}
