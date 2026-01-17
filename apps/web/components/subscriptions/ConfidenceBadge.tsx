"use client"

import { Info } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { getConfidenceColor } from "./utils"

export function ConfidenceBadge({ confidence, reason }: { confidence: string; reason: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border cursor-help",
            getConfidenceColor(confidence)
          )}
        >
          <Info className="w-3 h-3" />
          {confidence.charAt(0).toUpperCase() + confidence.slice(1)}
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-xs">
        <p>{reason}</p>
      </TooltipContent>
    </Tooltip>
  )
}
