"use client"

import * as React from "react"
import { Target } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { mockGoals, formatMYR, type Goal } from "@/lib/goals-data"

export interface GoalsProps {
  onAction?: () => void
  goals?: Goal[]
  className?: string
}

export function Goals({ onAction, goals: customGoals, className }: GoalsProps) {
  // Use all mock goals instead of slicing, or use custom goals if provided
  const goals = customGoals || mockGoals
  const hasGoals = goals.length > 0

  return (
    <Card className={cn("w-full border shadow-lg bg-background", className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="text-lg font-semibold">Goals</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              {hasGoals ? `Tracking ${goals.length} active goals` : "What is my active goal?"}
            </p>
          </div>

          {!hasGoals && (
            <Badge variant="outline" className="shrink-0">
              No goal
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-2">
        {hasGoals ? (
          <div className="space-y-4">
            {goals.map((goal) => {
              const progressPct = Math.round((goal.current / goal.target) * 100)
              const statusLabel = goal.status === "behind" ? "Behind" : "On track"
              const statusClass =
                goal.status === "behind"
                  ? "bg-warning/10 text-warning-foreground border-warning/30"
                  : "bg-success/10 text-success-foreground border-success/30"

              return (
                <div key={goal.id} className="p-3 rounded-lg bg-muted/50 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <Target className="w-4 h-4 text-muted-foreground shrink-0" />
                        <p className="text-sm font-medium truncate">{goal.name}</p>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {goal.deadline ?? "No deadline"} · {formatMYR(goal.target)}
                      </p>
                    </div>
                    <Badge className={cn("shrink-0", statusClass)}>{statusLabel}</Badge>
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <p className="text-xs text-muted-foreground">Progress</p>
                      <p className="text-xs font-medium">{progressPct}%</p>
                    </div>
                    <div className="h-2 w-full rounded-full bg-background">
                      <div
                        className={cn(
                          "h-full rounded-full",
                          goal.status === "behind" ? "bg-warning" : "bg-primary"
                        )}
                        style={{ width: `${Math.min(100, Math.max(0, progressPct))}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {formatMYR(goal.current)} / {formatMYR(goal.target)}
                    </p>
                  </div>

                  <p className="text-xs text-muted-foreground">{goal.nextAction}</p>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-sm">No active goal yet.</p>
            <p className="text-xs text-muted-foreground">
              Create a goal to track progress and get next-step suggestions.
            </p>
          </div>
        )}
      </CardContent>

      <CardFooter className="pt-2">
        <Button className="w-full" onClick={onAction}>
          {hasGoals ? "View all plans" : "Create a goal"}
        </Button>
      </CardFooter>
    </Card>
  )
}
