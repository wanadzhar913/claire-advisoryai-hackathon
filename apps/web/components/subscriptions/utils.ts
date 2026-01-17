export const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount)
}

export const getMonthlyEquivalent = (amount: number, frequency: string) => {
  switch (frequency) {
    case "yearly":
      return amount / 12
    case "weekly":
      return amount * 4.33
    default:
      return amount
  }
}

export const getConfidenceColor = (confidence: string) => {
  switch (confidence) {
    case "high":
      return "text-emerald-600 bg-emerald-50 border-emerald-200"
    case "medium":
      return "text-amber-600 bg-amber-50 border-amber-200"
    case "low":
      return "text-rose-600 bg-rose-50 border-rose-200"
    default:
      return "text-muted-foreground bg-muted"
  }
}

export const getFlagColor = (flag: string) => {
  switch (flag) {
    case "price increase":
      return "bg-orange-100 text-orange-700 border-orange-200"
    case "possible duplicate":
      return "bg-purple-100 text-purple-700 border-purple-200"
    case "multiple charges":
      return "bg-blue-100 text-blue-700 border-blue-200"
    case "low confidence":
      return "bg-rose-100 text-rose-700 border-rose-200"
    case "review":
      return "bg-amber-100 text-amber-700 border-amber-200"
    default:
      return "bg-muted text-muted-foreground"
  }
}
