export type EarnExtraPlanStatus = "generated" | "active" | "completed" | "archived"

export type PlanActionType = "cut_spend" | "shift_spend" | "increase_income" | "one_time_cleanup"

export type PlanAction = {
  label: string
  type: PlanActionType
  weekly_frequency?: number | null
  estimated_value?: number | null
}

export type PlanActionProgress = {
  is_done: boolean
  notes?: string | null
}

export type EarnExtraPlan = {
  id: string
  user_id: number
  file_id?: string | null
  status: EarnExtraPlanStatus
  target_amount: number
  currency: string
  timeframe_days: number
  title: string
  summary: string
  actions: PlanAction[]
  expected_amount?: number | null
  confidence?: "low" | "med" | "high" | string | null
  saved_so_far: number
  actions_progress: PlanActionProgress[]
  created_at?: string | null
  updated_at?: string | null
}

export function formatRM(value: number) {
  return `RM ${value.toLocaleString("en-MY")}`
}
