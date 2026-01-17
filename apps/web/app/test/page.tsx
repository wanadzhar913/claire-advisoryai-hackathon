"use client"

import { UploadForm } from "@/components/UploadForm"
import { Summary } from "@/components/Summary"
import { SankeyDiagram } from "@/components/SankeyDiagram"
import { Subscriptions } from "@/components/subscriptions"

export default function TestPage() {
  return (
    <main className="min-h-screen p-8 bg-muted/30">
      <div className="max-w-6xl mx-auto space-y-12">
        <section>
          <UploadForm 
            apiUrl="/api"
            onSuccess={(filename) => console.log("Upload successful:", filename)}
          />
        </section>

        <section>
          <h1 className="text-2xl font-bold mb-6">Cash Flow Visualization</h1>
          <SankeyDiagram />
        </section>

        <section>
          <h1 className="text-2xl font-bold mb-6">Subscriptions</h1>
          <Subscriptions />
        </section>
        
        <section className="flex items-center justify-center">
          <Summary 
            onClose={() => console.log("Close clicked")}
            onViewDetails={() => console.log("View details clicked")}
          />
        </section>
      </div>
    </main>
  )
}
