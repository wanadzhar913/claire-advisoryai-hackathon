export type SubscriptionAggregated = {
  merchant_key: string
  display_name: string
  category: string | null
  total_amount: number
  no_months_subscribed: number
  average_monthly_amount: number
  confidence_avg: number | null
  transaction_count: number
}

export type BankingTransaction = {
  id: string
  user_id: number
  file_id: string
  transaction_date: string
  transaction_year: number
  transaction_month: number
  transaction_day: number
  description: string
  merchant_name: string | null
  amount: number
  transaction_type: "debit" | "credit" | string
  is_subscription: boolean
  balance: number | null
  reference_number: string | null
  transaction_code: string | null
  category: string | null
  currency: string
  subscription_status: string | null
  subscription_confidence: number | null
  subscription_merchant_key: string | null
  subscription_name: string | null
  subscription_reason_codes: string[] | null
  subscription_updated_at: string | null
  created_at: string | null
}

export type ClassificationSummary = {
  total_processed: number
  predicted_count: number
  rejected_count: number
  needs_review_count: number
  failed_batches: unknown[]
  start_date: string
  end_date: string
}

