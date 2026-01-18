"use client";

import { SankeyDiagram } from "@/components/SankeyDiagram";
import { Subscriptions } from "@/components/subscriptions";
import { Goals } from "@/components/Goals";
import { EarnExtra } from "@/components/EarnExtra";
import { Summary } from "@/components/Summary";
import { ScopeSelector } from "@/components/ScopeSelector";
import { useScope } from "@/contexts/ScopeContext";

export default function DashboardPage() {
  const { scope, hasFiles, filesLoading } = useScope();

  return (
    <div className="space-y-6 p-6 min-w-0">
      <div className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Overview of your financial activity
          </p>
        </div>

        {/* Scope Selector */}
        <ScopeSelector />
      </div>

      {/* Show empty state if no files */}
      {!filesLoading && !hasFiles && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="rounded-full bg-muted p-4 mb-4">
            <svg
              className="h-8 w-8 text-muted-foreground"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold">No statements uploaded</h3>
          <p className="text-muted-foreground mt-1 max-w-sm">
            Upload a bank statement to see your financial overview and insights.
          </p>
        </div>
      )}

      {/* Dashboard content - only show when we have files and a scope */}
      {hasFiles && scope && (
        <div className="grid grid-cols-1 min-[988px]:grid-cols-3 gap-6">
          {/* Left Column */}
          <div className="min-[988px]:col-span-2 flex flex-col gap-6 min-w-0">
            <SankeyDiagram height={500} className="w-full" scope={scope} />
            <Subscriptions
              className="w-full flex-1"
              showFlaggedReview={true}
              scope={scope}
            />
          </div>

          {/* Right Column */}
          <div className="min-[988px]:col-span-1 flex flex-col gap-6 min-w-0">
            <Summary
              className="shrink-0"
              onClose={() => console.log("Close clicked")}
              onViewDetails={() => console.log("View details clicked")}
              scope={scope}
            />
            <Goals
              className="flex-1"
              onAction={() => console.log("Goal action clicked")}
            />
            <EarnExtra className="flex-1" />
          </div>
        </div>
      )}
    </div>
  );
}
