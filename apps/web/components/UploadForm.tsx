"use client";

import * as React from "react";
import { useAuth } from "@clerk/nextjs";
import {
  CloudUpload,
  FileText,
  Trash2,
  Loader2,
  AlertCircle,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface UploadFormProps {
  apiUrl: string;
  onSuccess: (filenames: string[]) => void;
}

export function UploadForm({ apiUrl, onSuccess }: UploadFormProps) {
  const { getToken } = useAuth();
  const [files, setFiles] = React.useState<File[]>([]);
  const [uploading, setUploading] = React.useState(false);
  const [uploadMode, setUploadMode] = React.useState<"upload" | "demo">(
    "upload",
  );
  const [error, setError] = React.useState<string | null>(null);
  const [dragging, setDragging] = React.useState(false);
  const [rangeStartMonth, setRangeStartMonth] = React.useState<number | "">("");
  const [rangeStartYear, setRangeStartYear] = React.useState<number | "">("");
  const [dragIndex, setDragIndex] = React.useState<number | null>(null);
  const [recentlyMovedKey, setRecentlyMovedKey] = React.useState<string | null>(
    null,
  );
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

  const validateFiles = (selectedFiles: File[]): string | null => {
    if (!selectedFiles.length) return "Please select at least 1 file.";
    if (selectedFiles.length > 3)
      return "Please upload up to 3 PDFs (for 1–3 consecutive months).";
    for (const f of selectedFiles) {
      if (f.type !== "application/pdf") {
        return "Only PDF files are allowed.";
      }
      if (f.size > MAX_FILE_SIZE_BYTES) {
        return `File size must be less than 10MB: ${f.name}`;
      }
    }
    return null;
  };

  const monthNames = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  const yearOptions = React.useMemo(() => {
    const currentYear = new Date().getFullYear();
    const years: number[] = [];
    for (let y = currentYear - 5; y <= currentYear + 1; y++) {
      years.push(y);
    }
    return years;
  }, []);

  const getMonthYearOffset = (
    month: number,
    year: number,
    offsetMonths: number,
  ) => {
    // offsetMonths can be negative (go backwards) or positive.
    const zeroBased = month - 1 + offsetMonths;
    const newYear = year + Math.floor(zeroBased / 12);
    const mod = ((zeroBased % 12) + 12) % 12;
    return { month: mod + 1, year: newYear };
  };

  const getAssignedMonthsForFiles = (
    latestMonth: number,
    latestYear: number,
    fileCount: number,
  ) => {
    // Business rule: user selects the *latest* month in the batch.
    // If they upload 2 PDFs and pick Jan 2026, we tag: Jan 2026 and Dec 2025.
    // Order returned is oldest -> newest, so it aligns with a typical statement timeline.
    const clampedCount = Math.max(1, Math.min(3, fileCount));
    const assigned: Array<{ month: number; year: number }> = [];
    for (let i = clampedCount - 1; i >= 0; i--) {
      assigned.push(getMonthYearOffset(latestMonth, latestYear, -i));
    }
    return assigned;
  };

  const handleFilesSelect = (selected: FileList | File[]) => {
    setError(null);
    const next = Array.from(selected);
    const validationError = validateFiles(next);
    if (validationError) {
      setFiles([]);
      setError(validationError);
      return;
    }
    setFiles(next);
  };

  const moveFile = (fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex) return;
    setFiles((prev) => {
      const next = [...prev];
      const [moved] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, moved);
      return next;
    });

    const moved = files[fromIndex];
    if (moved) {
      const key = `${moved.name}_${moved.size}_${moved.lastModified}`;
      setRecentlyMovedKey(key);
      window.setTimeout(() => {
        setRecentlyMovedKey((k) => (k === key ? null : k));
      }, 350);
    }
  };

  const moveUp = (index: number) => {
    if (index <= 0) return;
    moveFile(index, index - 1);
  };

  const moveDown = (index: number) => {
    if (index >= files.length - 1) return;
    moveFile(index, index + 1);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelect(e.dataTransfer.files);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFilesSelect(e.target.files);
    }
  };

  const clearFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setFiles([]);
    setError(null);
    setDragIndex(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUpload = async () => {
    if (!files.length) return;
    if (!apiUrl) {
      setError("API URL is not configured.");
      return;
    }

    if (rangeStartMonth === "" || rangeStartYear === "") {
      setError(
        "Please select the latest statement month and year for this upload.",
      );
      return;
    }

    if (files.length > 3) {
      setError("Please upload up to 3 PDFs (for 1–3 consecutive months).");
      return;
    }

    setUploadMode("upload");
    setUploading(true);
    setError(null);

    try {
      const token = await getToken();
      const headers: HeadersInit = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      // Backend expects a single month/year per upload (matches DB schema).
      // We upload each PDF individually and tag it with the correct month/year.
      const assigned = getAssignedMonthsForFiles(
        rangeStartMonth,
        rangeStartYear,
        files.length,
      );
      const filesOrderedOldestToNewest = [...files];

      await Promise.all(
        filesOrderedOldestToNewest.map(async (f, i) => {
          const tag = assigned[i];

          const fd = new FormData();
          fd.append("files", f);

          const url = new URL(`${apiUrl}/api/v1/file-uploads/upload`);
          url.searchParams.set("expense_month", String(tag.month));
          url.searchParams.set("expense_year", String(tag.year));

          const response = await fetch(url.toString(), {
            method: "POST",
            headers,
            body: fd,
          });

          if (!response.ok) {
            const errorText = await response
              .text()
              .catch(() => "Unknown error");
            throw new Error(errorText || "Upload failed");
          }
        }),
      );

      document.cookie = "demo_mode=; Max-Age=0; path=/";
      onSuccess(filesOrderedOldestToNewest.map((f) => f.name));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred",
      );
    } finally {
      setUploading(false);
    }
  };

  const handleDemo = async () => {
    if (!apiUrl) {
      setError("API URL is not configured.");
      return;
    }

    setUploadMode("demo");
    setUploading(true);
    setError(null);

    try {
      const token = await getToken();
      const headers: HeadersInit = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${apiUrl}/api/v1/file-uploads/demo`, {
        method: "POST",
        headers,
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => "Unknown error");
        throw new Error(errorText || "Demo load failed");
      }

      onSuccess(["demo_data.json"]);
      document.cookie = "demo_mode=1; path=/";
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred",
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card className="w-full border shadow-lg bg-background relative overflow-hidden">
      {/* Loading Overlay */}
      {uploading && (
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm z-50 flex flex-col items-center justify-center gap-4">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-primary/20 rounded-full" />
            <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-t-primary rounded-full animate-spin" />
          </div>
          <div className="text-center space-y-1">
            <p className="text-sm font-medium">
              {uploadMode === "demo"
                ? "Loading demo data..."
                : "Uploading your file..."}
            </p>
            <p className="text-xs text-muted-foreground">
              Please wait while we process your document
            </p>
            <p className="text-sm text-muted-foreground/70 pt-2">
              This may take several minutes (2-3 minutes) depending on your
              financial statement to process
            </p>
          </div>
        </div>
      )}
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-semibold">File Upload</CardTitle>
        </div>
        <CardDescription>
          Upload 2-3 months of consecutive financial statements (e.g., JanMar)
          for better insights. Select the latest month in your upload batch so
          we can tag each PDF correctly.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        <div className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Latest statement month{" "}
                <span className="text-destructive">*</span>
              </label>
              <Select
                value={rangeStartMonth === "" ? "" : String(rangeStartMonth)}
                onValueChange={(v) =>
                  setRangeStartMonth(v === "" ? "" : Number(v))
                }
                disabled={uploading}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select month" />
                </SelectTrigger>
                <SelectContent>
                  {monthNames.map((name, idx) => (
                    <SelectItem key={name} value={String(idx + 1)}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                Latest statement year{" "}
                <span className="text-destructive">*</span>
              </label>
              <Select
                value={rangeStartYear === "" ? "" : String(rangeStartYear)}
                onValueChange={(v) =>
                  setRangeStartYear(v === "" ? "" : Number(v))
                }
                disabled={uploading}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select year" />
                </SelectTrigger>
                <SelectContent>
                  {yearOptions.map((y) => (
                    <SelectItem key={y} value={String(y)}>
                      {y}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="text-xs text-muted-foreground">
            {rangeStartMonth !== "" && rangeStartYear !== "" ? (
              (() => {
                const assigned = getAssignedMonthsForFiles(
                  rangeStartMonth,
                  rangeStartYear,
                  Math.max(1, files.length || 1),
                );
                const label = assigned
                  .map((x) => `${monthNames[x.month - 1]} ${x.year}`)
                  .join(" - ");
                return (
                  <span>
                    PDFs will be tagged as:{" "}
                    <span className="font-medium text-foreground">{label}</span>
                  </span>
                );
              })()
            ) : (
              <span>
                Select a month/year and we'll automatically tag 1-3 PDFs as
                consecutive months (going backwards).
              </span>
            )}
          </div>
        </div>

        <div
          onClick={() => !uploading && fileInputRef.current?.click()}
          onDragOver={!uploading ? onDragOver : undefined}
          onDragLeave={!uploading ? onDragLeave : undefined}
          onDrop={!uploading ? onDrop : undefined}
          className={cn(
            "relative flex flex-col items-center justify-center py-12 rounded-xl border-2 border-dashed transition-all duration-200 ease-in-out cursor-pointer",
            dragging
              ? "border-primary bg-primary/10"
              : "border-border hover:border-primary hover:bg-muted/50",
            uploading && "opacity-50 cursor-not-allowed",
            error && "border-destructive/50 bg-destructive/5",
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={handleInputChange}
            disabled={uploading}
            multiple
          />

          <div className="flex flex-col items-center text-center space-y-3">
            <div className="p-3 bg-card rounded-full shadow-sm">
              <CloudUpload className="w-8 h-8 text-primary" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">
                <span className="text-primary">Click to upload</span> or drag
                and drop
              </p>
              <p className="text-xs text-muted-foreground">
                PDF (max 10MB each). Upload 2-3 files for consecutive months.
              </p>
            </div>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-sm text-destructive justify-center">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        )}

        {files.length > 0 && (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Drag to reorder. <span className="font-medium">#1</span> is
              treated as the <span className="font-medium">oldest</span>{" "}
              statement and gets the earliest month.
            </p>
            <div className="space-y-2">
              {files.map((file, idx) => {
                const fileKey = `${file.name}_${file.size}_${file.lastModified}`;
                return (
                  <div
                    key={fileKey}
                    draggable={!uploading}
                    onDragStart={() => {
                      if (uploading) return;
                      setDragIndex(idx);
                    }}
                    onDragOver={(e) => {
                      if (uploading) return;
                      e.preventDefault();
                    }}
                    onDrop={(e) => {
                      if (uploading) return;
                      e.preventDefault();
                      if (dragIndex === null) return;
                      moveFile(dragIndex, idx);
                      setDragIndex(null);
                    }}
                    onDragEnd={() => setDragIndex(null)}
                    className={cn(
                      "relative flex items-center justify-between p-3 border rounded-lg bg-background group transition-colors",
                      "transition-all duration-200 ease-out",
                      uploading
                        ? "opacity-60 cursor-not-allowed"
                        : "cursor-move hover:border-primary/50",
                      dragIndex === idx && "border-primary",
                      recentlyMovedKey === fileKey &&
                        "ring-2 ring-primary/40 bg-primary/5",
                    )}
                    title={uploading ? undefined : "Drag to reorder"}
                  >
                    <span className="absolute -top-2 -left-2 inline-flex items-center justify-center h-6 min-w-6 px-1.5 rounded-full bg-primary text-primary-foreground text-[11px] font-semibold shadow-sm ring-2 ring-background">
                      {idx + 1}
                    </span>

                    <div className="flex items-center gap-3 overflow-hidden">
                      <div className="p-2 bg-destructive/10 rounded-lg shrink-0">
                        <FileText className="w-5 h-5 text-destructive" />
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className="text-sm font-medium truncate pr-4">
                          {file.name}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {(file.size / (1024 * 1024)).toFixed(2)} MB
                        </span>
                      </div>
                    </div>

                    {/* Mobile-friendly reorder controls */}
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        onClick={() => moveUp(idx)}
                        disabled={uploading || idx === 0}
                        className={cn(
                          "inline-flex items-center justify-center h-8 w-8 rounded-md border bg-background",
                          uploading || idx === 0
                            ? "opacity-40 cursor-not-allowed"
                            : "hover:bg-muted",
                        )}
                        aria-label="Move file up"
                        title="Move up"
                      >
                        <ArrowUp className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => moveDown(idx)}
                        disabled={uploading || idx === files.length - 1}
                        className={cn(
                          "inline-flex items-center justify-center h-8 w-8 rounded-md border bg-background",
                          uploading || idx === files.length - 1
                            ? "opacity-40 cursor-not-allowed"
                            : "hover:bg-muted",
                        )}
                        aria-label="Move file down"
                        title="Move down"
                      >
                        <ArrowDown className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                );
              })}

              {!uploading && (
                <div className="flex justify-end">
                  <button
                    onClick={clearFile}
                    className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-full hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    Clear all
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="flex justify-end gap-3 pt-2">
        <Button variant="outline" onClick={handleDemo} disabled={uploading}>
          Use demo data
        </Button>
        <Button
          variant="outline"
          onClick={clearFile}
          disabled={!files.length || uploading}
        >
          Cancel
        </Button>
        <Button
          onClick={handleUpload}
          disabled={!files.length || uploading}
          className="bg-primary hover:bg-primary/90 text-primary-foreground min-w-25"
        >
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Uploading...
            </>
          ) : (
            "Next"
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
