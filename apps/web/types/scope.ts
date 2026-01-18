/**
 * Types for the scope selector feature.
 * Allows users to view analytics either by single statement or by date range.
 */

// Scope type discriminated union
export type StatementScope = {
  type: "statement";
  fileId: string;
};

export type RangeScope = {
  type: "range";
  startDate: string; // YYYY-MM-DD format
  endDate: string; // YYYY-MM-DD format
};

export type Scope = StatementScope | RangeScope;

// User file/upload types
export type FileStatus = "processed" | "processing" | "failed";

export interface UserFile {
  file_id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  file_url: string;
  statement_type: string;
  expense_month: number;
  expense_year: number;
  created_at: string | null;
  status?: FileStatus;
  period_start_date?: string | null;
  period_end_date?: string | null;
}

export interface UserFilesResponse {
  uploads: UserFile[];
  count: number;
  limit: number;
  offset: number;
}

// Date range presets
export type RangePreset =
  | "last_30_days"
  | "last_90_days"
  | "this_month"
  | "last_3_months"
  | "ytd"
  | "custom";

export interface RangePresetOption {
  id: RangePreset;
  label: string;
  getRange: () => { startDate: string; endDate: string };
}

// Helper function to format date to YYYY-MM-DD
export function formatDateToISO(date: Date): string {
  return date.toISOString().split("T")[0];
}

// Helper function to get month/year label from a file
export function getFileMonthYearLabel(file: UserFile): string {
  const monthNames = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  return `${monthNames[file.expense_month - 1]} ${file.expense_year}`;
}

// Helper function to get upload time label
export function getFileUploadTimeLabel(file: UserFile): string {
  if (!file.created_at) return "";
  const date = new Date(file.created_at);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

// Date range preset configurations
export function getRangePresets(): RangePresetOption[] {
  const today = new Date();

  return [
    {
      id: "last_30_days",
      label: "Last 30 days",
      getRange: () => {
        const endDate = new Date(today);
        const startDate = new Date(today);
        startDate.setDate(startDate.getDate() - 30);
        return {
          startDate: formatDateToISO(startDate),
          endDate: formatDateToISO(endDate),
        };
      },
    },
    {
      id: "last_90_days",
      label: "Last 90 days",
      getRange: () => {
        const endDate = new Date(today);
        const startDate = new Date(today);
        startDate.setDate(startDate.getDate() - 90);
        return {
          startDate: formatDateToISO(startDate),
          endDate: formatDateToISO(endDate),
        };
      },
    },
    {
      id: "this_month",
      label: "This month",
      getRange: () => {
        const startDate = new Date(today.getFullYear(), today.getMonth(), 1);
        const endDate = new Date(today);
        return {
          startDate: formatDateToISO(startDate),
          endDate: formatDateToISO(endDate),
        };
      },
    },
    {
      id: "last_3_months",
      label: "Last 3 months",
      getRange: () => {
        const endDate = new Date(today);
        const startDate = new Date(today);
        startDate.setMonth(startDate.getMonth() - 3);
        return {
          startDate: formatDateToISO(startDate),
          endDate: formatDateToISO(endDate),
        };
      },
    },
    {
      id: "ytd",
      label: "Year to date",
      getRange: () => {
        const startDate = new Date(today.getFullYear(), 0, 1);
        const endDate = new Date(today);
        return {
          startDate: formatDateToISO(startDate),
          endDate: formatDateToISO(endDate),
        };
      },
    },
    {
      id: "custom",
      label: "Custom range",
      getRange: () => {
        // Custom range requires user input
        const endDate = new Date(today);
        const startDate = new Date(today);
        startDate.setDate(startDate.getDate() - 30);
        return {
          startDate: formatDateToISO(startDate),
          endDate: formatDateToISO(endDate),
        };
      },
    },
  ];
}
