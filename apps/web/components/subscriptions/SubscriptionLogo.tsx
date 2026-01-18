"use client"

import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"
import { getLogoForSubscription, getInitials } from "./logoMap"

interface SubscriptionLogoProps {
  name: string
  logo?: string
}

export function SubscriptionLogo({ name, logo }: SubscriptionLogoProps) {
  const resolvedLogo = logo || getLogoForSubscription(name)
  const initials = getInitials(name)

  return (
    <Avatar className="w-10 h-10 border border-border">
      {resolvedLogo && (
        <AvatarImage
          src={resolvedLogo}
          alt={`${name} logo`}
          className="object-cover"
        />
      )}
      <AvatarFallback className="bg-muted text-muted-foreground font-semibold text-sm">
        {initials}
      </AvatarFallback>
    </Avatar>
  )
}
