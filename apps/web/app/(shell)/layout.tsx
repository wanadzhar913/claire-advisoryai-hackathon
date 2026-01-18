"use client"

import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/AppSidebar"
import { ScopeProvider } from "@/contexts/ScopeContext"

export default function ShellLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ScopeProvider>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger className="-ml-1" />
            <div className="flex-1" />
          </header>
          <main className="flex-1 overflow-x-hidden overflow-y-auto p-4 md:p-6">
            <div className="max-w-full">
              {children}
            </div>
          </main>
        </SidebarInset>
      </SidebarProvider>
    </ScopeProvider>
  )
}
