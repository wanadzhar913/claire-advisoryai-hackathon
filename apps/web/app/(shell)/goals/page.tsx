"use client"

import { useEffect, useMemo, useState } from "react"
import Image from "next/image"
import { LayoutGrid, List as ListIcon, Plus, Target, Check } from "lucide-react"

import { Goals } from "@/components/Goals"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useApi } from "@/hooks/use-api"
import { formatMYR, type Goal, type GoalStatus } from "@/lib/goals-data"
import { cn } from "@/lib/utils"

const BANNER_OPTIONS = [
  "/banners/banner_1.jpg",
  "/banners/banner_2.jpg",
  "/banners/banner_3.jpg",
  "/banners/banner_4.jpg",
]

type BackendGoal = {
  id: string
  user_id: number
  name: string
  target_amount: number | string
  current_saved: number | string
  target_year: number
  target_month: number
  banner_key: string
  created_at?: string | null
}

type BannerKey = "banner_1" | "banner_2" | "banner_3" | "banner_4"

function bannerKeyFromImageUrl(imageUrl: string): BannerKey {
  const filename = imageUrl.split("/").pop() ?? ""
  const key = filename.replace(".jpg", "") as BannerKey
  if (key === "banner_1" || key === "banner_2" || key === "banner_3" || key === "banner_4") return key
  return "banner_1"
}

function imageUrlFromBannerKey(bannerKey: string): string | undefined {
  if (bannerKey === "banner_1" || bannerKey === "banner_2" || bannerKey === "banner_3" || bannerKey === "banner_4") {
    return `/banners/${bannerKey}.jpg`
  }
  return undefined
}

function deadlineFromYearMonth(year: number, month: number): string {
  const date = new Date(year, Math.max(0, month - 1), 1)
  return date.toLocaleDateString("en-US", { month: "short", year: "numeric" })
}

function statusFromProgress(progress: number): GoalStatus {
  if (!Number.isFinite(progress) || progress <= 0.25) return "behind"
  return "on-track"
}

function nextActionFromStatus(status: GoalStatus): string {
  return status === "behind" ? "Consider increasing your monthly savings toward this goal." : "Keep going — you’re on track."
}

function mapBackendGoalToUi(goal: BackendGoal): Goal {
  const target = Number(goal.target_amount)
  const current = Number(goal.current_saved)
  const progress = target > 0 ? current / target : 0
  const status = statusFromProgress(progress)

  return {
    id: goal.id,
    name: goal.name,
    target,
    current,
    deadline: deadlineFromYearMonth(goal.target_year, goal.target_month),
    status,
    nextAction: nextActionFromStatus(status),
    imageUrl: imageUrlFromBannerKey(goal.banner_key),
  }
}

export default function GoalsPage() {
  const [view, setView] = useState<"grid" | "list">("grid")
  const [goals, setGoals] = useState<Goal[]>([])
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)

  const { get, post, isLoaded, isSignedIn } = useApi()
  const [isLoadingGoals, setIsLoadingGoals] = useState(false)
  const [goalsError, setGoalsError] = useState<string | null>(null)

  const canLoadGoals = useMemo(() => isLoaded && isSignedIn, [isLoaded, isSignedIn])
  const showEmptyState = useMemo(
    () => canLoadGoals && !isLoadingGoals && !goalsError && goals.length === 0,
    [canLoadGoals, goals.length, goalsError, isLoadingGoals]
  )

  useEffect(() => {
    if (!isLoaded) return
    if (!isSignedIn) {
      setGoals([])
      setGoalsError(null)
      return
    }

    let isCancelled = false

    async function loadGoals() {
      setIsLoadingGoals(true)
      setGoalsError(null)
      try {
        const result = await get<BackendGoal[]>("/api/v1/goals")
        if (isCancelled) return
        setGoals(result.map(mapBackendGoalToUi))
      } catch (e) {
        if (isCancelled) return
        const message = e instanceof Error ? e.message : "Failed to load goals"
        setGoalsError(message)
      } finally {
        if (!isCancelled) setIsLoadingGoals(false)
      }
    }

    void loadGoals()

    return () => {
      isCancelled = true
    }
  }, [get, isLoaded, isSignedIn])

  async function createGoalFromUi(newGoal: Goal, bannerKey: BannerKey, targetDate: string) {
    const now = new Date()
    const [yearStr, monthStr] = targetDate.split("-")
    const parsedYear = Number(yearStr)
    const parsedMonth = Number(monthStr)
    const targetYear = Number.isFinite(parsedYear) && parsedYear > 1900 ? parsedYear : now.getFullYear()
    const targetMonth =
      Number.isFinite(parsedMonth) && parsedMonth >= 1 && parsedMonth <= 12 ? parsedMonth : now.getMonth() + 1

    const created = await post<BackendGoal>("/api/v1/goals", {
      name: newGoal.name,
      target_amount: newGoal.target,
      current_saved: newGoal.current,
      target_year: targetYear,
      target_month: targetMonth,
      banner_key: bannerKey,
    })

    const createdUi = mapBackendGoalToUi(created)
    setGoals((prev) => [createdUi, ...prev])
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Goals</h1>
          <p className="text-muted-foreground mt-2">
            Track your financial goals and progress
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center border rounded-md p-1 bg-muted/50">
            <Button
              variant={view === "grid" ? "secondary" : "ghost"}
              size="sm"
              className="h-8 w-8 p-0"
              onClick={() => setView("grid")}
            >
              <LayoutGrid className="h-4 w-4" />
              <span className="sr-only">Grid view</span>
            </Button>
            <Button
              variant={view === "list" ? "secondary" : "ghost"}
              size="sm"
              className="h-8 w-8 p-0"
              onClick={() => setView("list")}
            >
              <ListIcon className="h-4 w-4" />
              <span className="sr-only">List view</span>
            </Button>
          </div>
          <Button size="sm" className="h-10 gap-2" onClick={() => setIsAddModalOpen(true)}>
            <Plus className="h-6 w-4" />
            Add Goal
          </Button>
        </div>
      </div>

      {!isLoaded && (
        <p className="text-sm text-muted-foreground">Loading…</p>
      )}

      {isLoaded && !isSignedIn && (
        <p className="text-sm text-muted-foreground">Sign in to load your goals.</p>
      )}

      {canLoadGoals && isLoadingGoals && (
        <p className="text-sm text-muted-foreground">Fetching goals…</p>
      )}

      {canLoadGoals && goalsError && (
        <p className="text-sm text-destructive">Failed to load goals: {goalsError}</p>
      )}

      {view === "list" ? (
        <Goals goals={goals} onAction={() => setIsAddModalOpen(true)} />
      ) : showEmptyState ? (
        <Card className="border-dashed bg-muted/20">
          <CardContent className="py-14">
            <div className="mx-auto max-w-md text-center space-y-4">
              <div className="mx-auto h-12 w-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
                <Target className="h-6 w-6" />
              </div>
              <div className="space-y-1.5">
                <h2 className="text-lg font-semibold tracking-tight">No goals yet</h2>
                <p className="text-sm text-muted-foreground">
                  Create your first goal to start tracking progress and stay on target.
                </p>
              </div>
              <div className="flex items-center justify-center gap-2">
                <Button onClick={() => setIsAddModalOpen(true)} className="gap-2">
                  <Plus className="h-4 w-4" />
                  Create a goal
                </Button>
                <Badge variant="outline" className="text-xs">
                  Tip: start with an emergency fund
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {goals.map((goal) => (
            <GoalCard key={goal.id} goal={goal} />
          ))}
        </div>
      )}

      <AddGoalDialog
        open={isAddModalOpen}
        onOpenChange={setIsAddModalOpen}
        onAddGoal={async (newGoal, bannerKey, targetDate) => {
          await createGoalFromUi(newGoal, bannerKey, targetDate)
          setIsAddModalOpen(false)
        }}
      />
    </div>
  )
}

function GoalCard({ goal }: { goal: Goal }) {
  const progressPct = Math.round((goal.current / goal.target) * 100)
  const statusLabel = goal.status === "behind" ? "Behind" : "On track"
  const statusClass =
    goal.status === "behind"
      ? "bg-warning/10 text-warning-foreground border-warning/30"
      : "bg-success/10 text-success-foreground border-success/30"

  return (
    <Card className="flex flex-col overflow-hidden transition-all hover:shadow-md">
      <div className="h-42 bg-muted/30 w-full relative group overflow-hidden rounded-t-4xl">
        {goal.imageUrl ? (
          <Image
            src={goal.imageUrl}
            alt={goal.name}
            fill
            className="object-cover transition-transform duration-500 group-hover:scale-105 rounded-t-4xl"
          />
        ) : (
          <div className="absolute border-2 border-border inset-0 flex items-center justify-center text-muted-foreground/10 group-hover:text-muted-foreground/20 transition-colors rounded-xl">
            <Target className="h-16 w-16" />
          </div>
        )}
        <div className="absolute top-3 right-3 z-10">
          <Badge className={cn("font-normal shadow-sm", statusClass)} variant="outline">
            {statusLabel}
          </Badge>
        </div>
      </div>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg leading-tight">{goal.name}</CardTitle>
        <p className="text-xs text-muted-foreground">
          {goal.deadline ? `Target: ${goal.deadline}` : "No target/deadline"}
        </p>
      </CardHeader>
      <CardContent className="space-y-4 flex-1">
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground font-medium text-xs">Progress</span>
            <span className="font-bold text-xs">{progressPct}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500 ease-out",
                goal.status === "behind" ? "bg-warning" : "bg-primary"
              )}
              style={{ width: `${Math.min(100, Math.max(0, progressPct))}%` }}
            />
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground pt-0.5">
            <span className="font-medium text-foreground">{formatMYR(goal.current)}</span>
            <span>of {formatMYR(goal.target)}</span>
          </div>
        </div>
      </CardContent>
      <CardFooter className="pt-0">
        <Button variant="outline" className="w-full h-8 text-xs">
          View Details
        </Button>
      </CardFooter>
    </Card>
  )
}

interface AddGoalDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAddGoal: (goal: Goal, bannerKey: BannerKey, targetDate: string) => Promise<void>
}

function AddGoalDialog({ open, onOpenChange, onAddGoal }: AddGoalDialogProps) {
  const [name, setName] = useState("")
  const [targetAmount, setTargetAmount] = useState("")
  const [targetDate, setTargetDate] = useState("")
  const [currentSaved, setCurrentSaved] = useState("")
  const [selectedBanner, setSelectedBanner] = useState(BANNER_OPTIONS[0])

  const resetForm = () => {
    setName("")
    setTargetAmount("")
    setTargetDate("")
    setCurrentSaved("")
    setSelectedBanner(BANNER_OPTIONS[0])
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const target = parseFloat(targetAmount) || 0
    const current = parseFloat(currentSaved) || 0

    // Format the date as "MMM YYYY" (UI only). Backend uses a default if not provided.
    let formattedDeadline: string | null = null
    if (targetDate) {
      const date = new Date(targetDate + "-01") // Add day to make valid date
      formattedDeadline = date.toLocaleDateString("en-US", { month: "short", year: "numeric" })
    }

    const newGoal: Goal = {
      id: crypto.randomUUID(),
      name: name.trim(),
      target,
      current,
      deadline: formattedDeadline,
      status: "on-track",
      nextAction: "Keep saving towards your goal!",
      imageUrl: selectedBanner,
    }

    const bannerKey = bannerKeyFromImageUrl(selectedBanner)
    void onAddGoal(newGoal, bannerKey, targetDate).finally(() => {
      resetForm()
    })
  }

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      resetForm()
    }
    onOpenChange(newOpen)
  }

  const isFormValid = name.trim() && targetAmount && parseFloat(targetAmount) > 0

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create New Goal</DialogTitle>
          <DialogDescription>
            Set up a new savings goal to track your progress.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="goal-name">Goal Name</Label>
            <Input
              id="goal-name"
              placeholder="e.g., New Car"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="target-amount">Target Amount (MYR)</Label>
              <Input
                id="target-amount"
                type="number"
                placeholder="80000"
                min="1"
                value={targetAmount}
                onChange={(e) => setTargetAmount(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="current-saved">Current Saved (MYR)</Label>
              <Input
                id="current-saved"
                type="number"
                placeholder="5000"
                min="0"
                value={currentSaved}
                onChange={(e) => setCurrentSaved(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="target-date">Target Date</Label>
            <Input
              id="target-date"
              type="month"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label>Banner Image</Label>
            <div className="grid grid-cols-2 gap-3">
              {BANNER_OPTIONS.map((banner) => (
                <button
                  key={banner}
                  type="button"
                  onClick={() => setSelectedBanner(banner)}
                  className={cn(
                    "relative aspect-video rounded-lg overflow-hidden border-2 transition-all focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                    selectedBanner === banner
                      ? "border-primary ring-2 ring-primary/20"
                      : "border-muted hover:border-muted-foreground/30"
                  )}
                >
                  <Image
                    src={banner}
                    alt="Banner option"
                    fill
                    className="object-cover"
                  />
                  {selectedBanner === banner && (
                    <div className="absolute inset-0 bg-primary/20 flex items-center justify-center">
                      <div className="bg-primary text-primary-foreground rounded-full p-1">
                        <Check className="h-4 w-4" />
                      </div>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!isFormValid}>
              Create Goal
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
