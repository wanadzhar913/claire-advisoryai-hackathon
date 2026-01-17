"use client"

import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"

export function SubscriptionLogo({ name, logo }: { name: string; logo: string }) {
  return (
    <Avatar className="w-10 h-10 border border-border">
      <AvatarImage
        src={logo}
        alt={`${name} logo`}
        className="object-cover"
      />
      <AvatarFallback className="bg-muted text-muted-foreground font-semibold text-sm">
        {name.charAt(0).toUpperCase()}
      </AvatarFallback>
    </Avatar>
  )
}
