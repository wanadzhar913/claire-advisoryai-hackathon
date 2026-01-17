"use client"

import {
  MoreHorizontal,
  Check,
  X,
  Copy,
  Bell,
  RefreshCw,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Subscription } from "./types"

export function ActionMenu({
  subscription,
  onAction,
}: {
  subscription: Subscription
  onAction: (action: string, id: string) => void
}) {
  const handleCopyCancel = () => {
    const message = `I would like to cancel my ${subscription.name} subscription. My account is associated with the payment method ending in ${subscription.sourceRef.split("****")[1]}.`
    navigator.clipboard.writeText(message)
    onAction("copy_cancel", subscription.id)
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon-sm" onClick={(e) => e.stopPropagation()}>
          <MoreHorizontal className="w-4 h-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => onAction("keep", subscription.id)}>
          <Check className="w-4 h-4 mr-2" />
          Keep subscription
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onAction("cancel", subscription.id)}>
          <X className="w-4 h-4 mr-2" />
          Mark for cancellation
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onAction("not_subscription", subscription.id)}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Not a subscription
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleCopyCancel}>
          <Copy className="w-4 h-4 mr-2" />
          Copy cancellation message
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onAction("reminder", subscription.id)}>
          <Bell className="w-4 h-4 mr-2" />
          Add reminder
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
