"use client"

import { TrendingUp } from "lucide-react"
import { SankeyDiagram } from "@/components/SankeyDiagram"

export default function CashFlowPage() {
  return (
    <div className="space-y-8 min-w-0">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Cash Flow</h1>
        <p className="text-muted-foreground mt-2">
          Visualize your income and expenses flow
        </p>
      </div>

      <section className="min-w-0">
        <div className="w-full overflow-x-auto">
          <SankeyDiagram />
        </div>
      </section>
    </div>
  )
}
