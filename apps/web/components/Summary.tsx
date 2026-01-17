"use client"

import * as React from "react"
import { 
  X, 
  Coffee, 
  Utensils, 
  ArrowRightLeft, 
  TrendingUp,
  AlertTriangle,
  Lightbulb
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardFooter
} from "@/components/ui/card"

// Mock data representing AI-parsed bank statement insights
const mockData = {
  insights: [
    { 
      id: "coffee", 
      icon: "Coffee", 
      title: "Morning Coffee Habit",
      description: "You spend ~$4.50 on coffee around 8am on weekdays"
    },
    { 
      id: "dining", 
      icon: "Utensils", 
      title: "Weekend Dining",
      description: "Restaurant spending peaks on Saturdays, averaging $45"
    },
    { 
      id: "transfers", 
      icon: "ArrowRightLeft", 
      title: "Savings Pattern",
      description: "You transfer $500 to savings on the 1st of each month"
    },
  ],
  alerts: [
    { id: "unusual", message: "Unusual spending detected last Tuesday", severity: "warning" },
    { id: "budget", message: "Dining budget exceeded by 23%", severity: "warning" },
  ]
}

const iconMap: Record<string, React.ElementType> = {
  Coffee,
  Utensils,
  ArrowRightLeft,
  TrendingUp,
}

interface SummaryProps {
  onClose?: () => void
  onViewDetails?: () => void
  className?: string
}

export function Summary({ onClose, onViewDetails, className }: SummaryProps) {
  return (
    <Card className={cn("w-full border shadow-lg bg-background", className)}>
      {/* Header */}
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">Financial Summary</CardTitle>
          {onClose && (
            <button 
              onClick={onClose}
              className="p-1.5 rounded-full hover:bg-muted transition-colors"
            >
              <X className="w-5 h-5 text-muted-foreground" />
            </button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-5 pt-2">
        {/* Spending Patterns */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="w-4 h-4 text-warning" />
            <h3 className="text-sm font-medium">Spending Insights</h3>
          </div>
          <div className="space-y-3">
            {mockData.insights.map((insight) => {
              const IconComponent = iconMap[insight.icon]
              return (
                <div
                  key={insight.id}
                  className="flex items-start gap-3 p-3 rounded-lg bg-muted/50"
                >
                  {IconComponent && (
                    <div className="p-2 rounded-lg bg-background shrink-0">
                      <IconComponent className="w-4 h-4 text-muted-foreground" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{insight.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{insight.description}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        {/* Alerts */}
        <section>
          <h3 className="text-sm font-medium mb-3">Alerts</h3>
          <div className="space-y-2">
            {mockData.alerts.map((alert) => (
              <div 
                key={alert.id}
                className="flex items-center gap-2 text-sm"
              >
                <AlertTriangle className={cn(
                  "w-4 h-4 shrink-0",
                  alert.severity === "warning" ? "text-warning" : "text-info"
                )} />
                <span className="text-muted-foreground">{alert.message}</span>
              </div>
            ))}
          </div>
        </section>
      </CardContent>
    </Card>
  )
}
