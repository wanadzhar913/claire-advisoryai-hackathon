"use client";

import * as React from "react";
import { useState, useMemo } from "react";
import {
  FileText,
  Calendar,
  ChevronDown,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useScope } from "@/contexts/ScopeContext";
import {
  type Scope,
  type RangePreset,
  type UserFile,
  getRangePresets,
  getFileMonthYearLabel,
  getFileUploadTimeLabel,
  formatDateToISO,
} from "@/types/scope";

type ScopeMode = "statement" | "range";

interface ScopeSelectorProps {
  className?: string;
}

export function ScopeSelector({ className }: ScopeSelectorProps) {
  const { scope, setScope, files, filesLoading, filesError, hasFiles } =
    useScope();

  // Local state for mode toggle
  const [mode, setMode] = useState<ScopeMode>(scope?.type || "statement");

  // Local state for range dates (for custom range)
  const [customStartDate, setCustomStartDate] = useState<string>("");
  const [customEndDate, setCustomEndDate] = useState<string>("");
  const [selectedPreset, setSelectedPreset] =
    useState<RangePreset>("last_30_days");

  // Get presets
  const presets = useMemo(() => getRangePresets(), []);

  // Group files by month/year for display
  const groupedFiles = useMemo(() => {
    const groups: Record<string, UserFile[]> = {};

    files.forEach((file) => {
      const key = getFileMonthYearLabel(file);
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(file);
    });

    return groups;
  }, [files]);

  // Get label for current file selection
  const getSelectedFileLabel = (): string => {
    if (!scope || scope.type !== "statement") return "Select statement";

    const file = files.find((f) => f.file_id === scope.fileId);
    if (!file) return "Select statement";

    const label = getFileMonthYearLabel(file);
    const filesInSameMonth = groupedFiles[label] || [];

    // If there are duplicates, show upload time
    if (filesInSameMonth.length > 1) {
      const uploadTime = getFileUploadTimeLabel(file);
      return uploadTime ? `${label} • ${uploadTime}` : label;
    }

    return label;
  };

  // Get label for current range selection
  const getRangeLabel = (): string => {
    if (!scope || scope.type !== "range") {
      const preset = presets.find((p) => p.id === selectedPreset);
      return preset?.label || "Select range";
    }

    // Format dates for display
    const startDate = new Date(scope.startDate);
    const endDate = new Date(scope.endDate);

    const formatDate = (date: Date) => {
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year:
          date.getFullYear() !== new Date().getFullYear()
            ? "numeric"
            : undefined,
      });
    };

    return `${formatDate(startDate)} – ${formatDate(endDate)}`;
  };

  // Handle mode change
  const handleModeChange = (newMode: ScopeMode) => {
    setMode(newMode);

    if (newMode === "statement" && hasFiles) {
      // Switch to latest file
      const latestFile = files[0];
      if (latestFile) {
        setScope({
          type: "statement",
          fileId: latestFile.file_id,
        });
      }
    } else if (newMode === "range") {
      // Switch to default preset range
      const preset = presets.find((p) => p.id === selectedPreset);
      if (preset) {
        const range = preset.getRange();
        setScope({
          type: "range",
          startDate: range.startDate,
          endDate: range.endDate,
        });
      }
    }
  };

  // Handle file selection
  const handleFileSelect = (fileId: string) => {
    setScope({
      type: "statement",
      fileId,
    });
  };

  // Handle preset selection
  const handlePresetSelect = (presetId: RangePreset) => {
    setSelectedPreset(presetId);

    if (presetId === "custom") {
      // For custom, we'll show date inputs
      return;
    }

    const preset = presets.find((p) => p.id === presetId);
    if (preset) {
      const range = preset.getRange();
      setScope({
        type: "range",
        startDate: range.startDate,
        endDate: range.endDate,
      });
    }
  };

  // Handle custom date change
  const handleCustomDateChange = (type: "start" | "end", value: string) => {
    if (type === "start") {
      setCustomStartDate(value);
    } else {
      setCustomEndDate(value);
    }

    // Update scope if both dates are set
    const start = type === "start" ? value : customStartDate;
    const end = type === "end" ? value : customEndDate;

    if (start && end && start <= end) {
      setScope({
        type: "range",
        startDate: start,
        endDate: end,
      });
    }
  };

  // Validation for custom range
  const isCustomRangeValid = (): boolean => {
    if (selectedPreset !== "custom") return true;
    return !!(
      customStartDate &&
      customEndDate &&
      customStartDate <= customEndDate
    );
  };

  const getValidationMessage = (): string | null => {
    if (selectedPreset !== "custom") return null;
    if (!customStartDate || !customEndDate) return "Please select both dates";
    if (customStartDate > customEndDate)
      return "Start date must be before end date";
    return null;
  };

  // Empty state
  if (filesLoading) {
    return (
      <div
        className={cn(
          "flex items-center gap-2 text-muted-foreground",
          className,
        )}
      >
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Loading...</span>
      </div>
    );
  }

  if (filesError) {
    return (
      <div
        className={cn("flex items-center gap-2 text-destructive", className)}
      >
        <AlertCircle className="h-4 w-4" />
        <span className="text-sm">{filesError}</span>
      </div>
    );
  }

  if (!hasFiles) {
    return (
      <div
        className={cn(
          "flex items-center gap-2 text-muted-foreground",
          className,
        )}
      >
        <AlertCircle className="h-4 w-4" />
        <span className="text-sm">No statements uploaded yet</span>
      </div>
    );
  }

  return (
    <div className={cn("flex items-center gap-2 flex-wrap", className)}>
      {/* Mode Toggle */}
      <div className="flex items-center rounded-lg border bg-muted/50 p-1">
        <Button
          variant={mode === "statement" ? "default" : "ghost"}
          size="sm"
          className="h-7 gap-1.5 px-2.5 text-xs"
          onClick={() => handleModeChange("statement")}
        >
          <FileText className="h-3.5 w-3.5" />
          Statement
        </Button>
        <Button
          variant={mode === "range" ? "default" : "ghost"}
          size="sm"
          className="h-7 gap-1.5 px-2.5 text-xs"
          onClick={() => handleModeChange("range")}
        >
          <Calendar className="h-3.5 w-3.5" />
          Range
        </Button>
      </div>

      {/* Statement Selector */}
      {mode === "statement" && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8 gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              {getSelectedFileLabel()}
              <ChevronDown className="h-3.5 w-3.5 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56">
            <DropdownMenuLabel>Select Statement</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {Object.entries(groupedFiles).map(([monthYear, filesInMonth]) => (
              <React.Fragment key={monthYear}>
                {filesInMonth.length === 1 ? (
                  <DropdownMenuItem
                    onClick={() => handleFileSelect(filesInMonth[0].file_id)}
                    className={cn(
                      scope?.type === "statement" &&
                        scope.fileId === filesInMonth[0].file_id &&
                        "bg-accent",
                    )}
                  >
                    <FileText className="h-4 w-4 mr-2 opacity-50" />
                    {monthYear}
                    {filesInMonth[0] === files[0] && (
                      <span className="ml-auto text-xs text-muted-foreground">
                        (latest)
                      </span>
                    )}
                  </DropdownMenuItem>
                ) : (
                  filesInMonth.map((file, idx) => (
                    <DropdownMenuItem
                      key={file.file_id}
                      onClick={() => handleFileSelect(file.file_id)}
                      className={cn(
                        scope?.type === "statement" &&
                          scope.fileId === file.file_id &&
                          "bg-accent",
                      )}
                    >
                      <FileText className="h-4 w-4 mr-2 opacity-50" />
                      {monthYear} • {getFileUploadTimeLabel(file)}
                      {file === files[0] && (
                        <span className="ml-auto text-xs text-muted-foreground">
                          (latest)
                        </span>
                      )}
                    </DropdownMenuItem>
                  ))
                )}
              </React.Fragment>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}

      {/* Range Selector */}
      {mode === "range" && (
        <div className="flex items-center gap-2 flex-wrap">
          {/* Preset Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 gap-1.5">
                <Calendar className="h-3.5 w-3.5" />
                {selectedPreset === "custom" ? "Custom" : getRangeLabel()}
                <ChevronDown className="h-3.5 w-3.5 opacity-50" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-48">
              <DropdownMenuLabel>Date Range</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {presets.map((preset) => (
                <DropdownMenuItem
                  key={preset.id}
                  onClick={() => handlePresetSelect(preset.id)}
                  className={cn(selectedPreset === preset.id && "bg-accent")}
                >
                  {preset.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Custom Date Inputs */}
          {selectedPreset === "custom" && (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={customStartDate}
                onChange={(e) =>
                  handleCustomDateChange("start", e.target.value)
                }
                className="h-8 rounded-md border border-input bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <span className="text-muted-foreground text-xs">to</span>
              <input
                type="date"
                value={customEndDate}
                onChange={(e) => handleCustomDateChange("end", e.target.value)}
                className="h-8 rounded-md border border-input bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
              />
              {getValidationMessage() && (
                <span className="text-xs text-destructive flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {getValidationMessage()}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
