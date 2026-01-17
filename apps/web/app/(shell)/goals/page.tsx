"use client"

import { Goals } from "@/components/Goals"

export default function GoalsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Goals</h1>
        <p className="text-muted-foreground mt-2">
          Track your financial goals and progress
        </p>
      </div>

      <Goals onAction={() => console.log("Goal action clicked")} />
    </div>
  )
}
