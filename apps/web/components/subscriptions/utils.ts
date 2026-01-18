export const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat("ms-MY", {
    style: "currency",
    currency: "MYR",
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
      return "text-success-foreground bg-success/10 border-success/30"
    case "medium":
      return "text-warning-foreground bg-warning/10 border-warning/30"
    case "low":
      return "text-destructive bg-destructive/10 border-destructive/30"
    default:
      return "text-muted-foreground bg-muted"
  }
}

export const getFlagColor = (flag: string) => {
  switch (flag) {
    case "price increase":
      return "bg-warning/10 text-warning-foreground border-warning/30"
    case "possible duplicate":
      return "bg-info/10 text-info-foreground border-info/30"
    case "multiple charges":
      return "bg-info/10 text-info-foreground border-info/30"
    case "low confidence":
      return "bg-destructive/10 text-destructive border-destructive/30"
    case "review":
      return "bg-warning/10 text-warning-foreground border-warning/30"
    default:
      return "bg-muted text-muted-foreground"
  }
}
