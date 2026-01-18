"use client";

import React, {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useState,
  useMemo,
} from "react";
import { useApi } from "@/hooks/use-api";
import type {
  Scope,
  UserFile,
  UserFilesResponse,
  formatDateToISO,
} from "@/types/scope";

interface ScopeContextValue {
  // Current scope
  scope: Scope | null;
  setScope: (scope: Scope) => void;

  // User files
  files: UserFile[];
  filesLoading: boolean;
  filesError: string | null;
  refreshFiles: () => Promise<void>;

  // Computed values
  hasFiles: boolean;
  latestFile: UserFile | null;

  // Query params helper - returns params to append to API calls
  getScopeParams: () => URLSearchParams;
  getScopeQueryString: () => string;
}

const ScopeContext = createContext<ScopeContextValue | undefined>(undefined);

export function ScopeProvider({ children }: { children: React.ReactNode }) {
  const { get, isSignedIn, isLoaded } = useApi();

  // Files state
  const [files, setFiles] = useState<UserFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(true);
  const [filesError, setFilesError] = useState<string | null>(null);

  // Scope state
  const [scope, setScope] = useState<Scope | null>(null);

  // Fetch user files
  const fetchFiles = useCallback(async () => {
    if (!isSignedIn) {
      setFilesLoading(false);
      return;
    }

    setFilesLoading(true);
    setFilesError(null);

    try {
      const response = await get<UserFilesResponse>(
        "/api/v1/file-uploads?limit=100&order_by=created_at&order_desc=true",
      );
      setFiles(response.uploads || []);
    } catch (err) {
      console.error("Failed to fetch files:", err);
      setFilesError("Failed to load files");
      setFiles([]);
    } finally {
      setFilesLoading(false);
    }
  }, [get, isSignedIn]);

  // Refresh files
  const refreshFiles = useCallback(async () => {
    await fetchFiles();
  }, [fetchFiles]);

  // Fetch files on mount and when auth changes
  useEffect(() => {
    if (isLoaded) {
      fetchFiles();
    }
  }, [isLoaded, isSignedIn, fetchFiles]);

  // Computed values
  const hasFiles = files.length > 0;
  const latestFile = useMemo(() => {
    if (files.length === 0) return null;
    // Files are already sorted by created_at desc from API
    return files[0];
  }, [files]);

  // Set default scope when files load
  useEffect(() => {
    if (!filesLoading && scope === null && hasFiles && latestFile) {
      // Default to statement mode with latest file
      setScope({
        type: "statement",
        fileId: latestFile.file_id,
      });
    }
  }, [filesLoading, scope, hasFiles, latestFile]);

  // Get scope params for API calls
  const getScopeParams = useCallback((): URLSearchParams => {
    const params = new URLSearchParams();

    if (!scope) return params;

    if (scope.type === "statement") {
      params.set("file_id", scope.fileId);
    } else if (scope.type === "range") {
      params.set("start_date", scope.startDate);
      params.set("end_date", scope.endDate);
    }

    return params;
  }, [scope]);

  // Get scope query string for API calls
  const getScopeQueryString = useCallback((): string => {
    const params = getScopeParams();
    const queryString = params.toString();
    return queryString ? `?${queryString}` : "";
  }, [getScopeParams]);

  const value: ScopeContextValue = {
    scope,
    setScope,
    files,
    filesLoading,
    filesError,
    refreshFiles,
    hasFiles,
    latestFile,
    getScopeParams,
    getScopeQueryString,
  };

  return (
    <ScopeContext.Provider value={value}>{children}</ScopeContext.Provider>
  );
}

export function useScope() {
  const context = useContext(ScopeContext);
  if (context === undefined) {
    throw new Error("useScope must be used within a ScopeProvider");
  }
  return context;
}
