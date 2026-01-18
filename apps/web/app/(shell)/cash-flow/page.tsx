"use client"

import { TrendingUp } from "lucide-react"
import { SankeyDiagram } from "@/components/SankeyDiagram"
import { ScopeSelector } from "@/components/ScopeSelector"
import { useScope } from "@/contexts/ScopeContext"

export default function CashFlowPage() {
  const { scope, hasFiles, filesLoading } = useScope()

  return (
    <div className="space-y-8 min-w-0">
      <div className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Cash Flow</h1>
          <p className="text-muted-foreground mt-2">
            Visualize your income and expenses flow
          </p>
        </div>
        
        {/* Scope Selector */}
        <ScopeSelector />
      </div>

      {/* Show empty state if no files */}
      {!filesLoading && !hasFiles && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="rounded-full bg-muted p-4 mb-4">
            <TrendingUp className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">No statements uploaded</h3>
          <p className="text-muted-foreground mt-1 max-w-sm">
            Upload a bank statement to see your cash flow analysis.
          </p>
        </div>
      )}

      {/* Cash flow content - only show when we have files and a scope */}
      {hasFiles && scope && (
        <section className="min-w-0">
          <div className="w-full overflow-x-auto">
            <SankeyDiagram scope={scope} />
          </div>
        </section>
      )}
    </div>
  )
}
