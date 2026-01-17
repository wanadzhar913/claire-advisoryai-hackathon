"use client"

import { SankeyDiagram } from "@/components/SankeyDiagram"
import { Subscriptions } from "@/components/subscriptions"
import { Goals } from "@/components/Goals"
import { Summary } from "@/components/Summary"

export default function DashboardPage() {
  return (
    <div className="space-y-8 min-w-0">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-2">
          Overview of your financial activity
        </p>
      </div>

      <section className="min-w-0">
        <h2 className="text-2xl font-semibold mb-4">Cash Flow Visualization</h2>
        <div className="w-full overflow-x-auto">
          <SankeyDiagram />
        </div>
      </section>

      <section className="min-w-0">
        <h2 className="text-2xl font-semibold mb-4">Subscriptions</h2>
        <Subscriptions />
      </section>
      
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-w-0">
        <Goals onAction={() => console.log("Goal action clicked")} />
        <Summary 
          onClose={() => console.log("Close clicked")}
          onViewDetails={() => console.log("View details clicked")}
        />
      </section>
    </div>
  )
}
