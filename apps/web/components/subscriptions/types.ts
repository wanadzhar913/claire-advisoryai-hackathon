export interface Charge {
  date: string
  amount: number
  description: string
}

export interface Subscription {
  id: string
  name: string
  logo: string
  amount: number
  frequency: "monthly" | "yearly" | "weekly"
  confidence: "high" | "medium" | "low"
  confidenceReason: string
  flags: string[]
  lastCharges: Charge[]
  category: string
  status: "active" | "marked_cancel" | "not_subscription"
  statementPeriod: string
  sourceRef: string
}
