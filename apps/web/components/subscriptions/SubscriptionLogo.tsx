"use client"

import { useState } from "react"

export function SubscriptionLogo({ name, logo }: { name: string; logo: string }) {
  const [imgError, setImgError] = useState(false)

  if (imgError) {
    return (
      <div className="w-10 h-10 rounded-lg bg-linear-to-br from-slate-100 to-slate-200 flex items-center justify-center text-slate-600 font-semibold text-sm border border-slate-200">
        {name.charAt(0).toUpperCase()}
      </div>
    )
  }

  return (
    <img
      src={logo}
      alt={`${name} logo`}
      className="w-10 h-10 rounded-lg object-cover border border-slate-200"
      onError={() => setImgError(true)}
    />
  )
}
