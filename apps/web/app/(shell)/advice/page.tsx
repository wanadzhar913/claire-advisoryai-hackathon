"use client"

import { Lightbulb } from "lucide-react"

export default function AdvicePage() {
  return (
    <div className="space-y-8 min-w-0">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Advice</h1>
        <p className="text-muted-foreground mt-2">
          Get personalized financial advice and insights
        </p>
      </div>

      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Lightbulb className="w-12 h-12 text-muted-foreground mb-4 opacity-50" />
        <p className="text-lg font-medium text-muted-foreground">
          Advice page coming soon
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          This page will provide personalized financial advice and recommendations.
        </p>
      </div>
    </div>
  )
}
