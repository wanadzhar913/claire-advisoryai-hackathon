"use client"

import * as React from "react"
import { CloudUpload, FileText, Trash2, Loader2, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter
} from "@/components/ui/card"

interface UploadFormProps {
  apiUrl: string
  onSuccess: (filename: string) => void
}

export function UploadForm({ apiUrl, onSuccess }: UploadFormProps) {
  const [file, setFile] = React.useState<File | null>(null)
  const [uploading, setUploading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [dragging, setDragging] = React.useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const validateFile = (file: File): string | null => {
    if (file.type !== "application/pdf") {
      return "Only PDF files are allowed."
    }
    if (file.size > 10 * 1024 * 1024) { // 10MB
      return "File size must be less than 10MB."
    }
    return null
  }

  const handleFileSelect = (selectedFile: File) => {
    setError(null)
    const validationError = validateFile(selectedFile)
    if (validationError) {
      setError(validationError)
      return
    }
    setFile(selectedFile)
  }

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(true)
  }

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0])
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(e.target.files[0])
    }
  }

  const clearFile = (e: React.MouseEvent) => {
    e.stopPropagation()
    setFile(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleUpload = async () => {
    if (!file) return
    if (!apiUrl) {
      setError("API URL is not configured.")
      return
    }

    setUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append("file", file)

      const response = await fetch(`${apiUrl}/upload`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const errorText = await response.text().catch(() => "Unknown error")
        throw new Error(errorText || "Upload failed")
      }

      onSuccess(file.name)
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred")
    } finally {
      setUploading(false)
    }
  }

  return (
    <Card className="w-full border shadow-lg bg-background">
      <CardHeader>
        <div className="flex items-center justify-between">
            <CardTitle className="text-xl font-semibold">File Upload</CardTitle>
        </div>
        <CardDescription>
            Add your documents here, and you can upload 1 file max
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-6">
        <div
          onClick={() => !uploading && fileInputRef.current?.click()}
          onDragOver={!uploading ? onDragOver : undefined}
          onDragLeave={!uploading ? onDragLeave : undefined}
          onDrop={!uploading ? onDrop : undefined}
          className={cn(
            "relative flex flex-col items-center justify-center py-12 rounded-xl border-2 border-dashed transition-all duration-200 ease-in-out cursor-pointer",
            dragging
              ? "border-blue-500 bg-blue-50/50"
              : "border-blue-200 hover:border-blue-400 hover:bg-slate-50",
            uploading && "opacity-50 cursor-not-allowed",
            error && "border-destructive/50 bg-destructive/5"
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={handleInputChange}
            disabled={uploading}
          />
          
          <div className="flex flex-col items-center text-center space-y-3">
             <div className="p-3 bg-white rounded-full shadow-sm">
                <CloudUpload className="w-8 h-8 text-blue-600" />
             </div>
             <div className="space-y-1">
                <p className="text-sm font-medium">
                   <span className="text-blue-600">Click to upload</span> or drag and drop
                </p>
                <p className="text-xs text-muted-foreground">
                   PDF (max 10MB)
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

        {file && (
          <div className="space-y-3">
             <div className="flex items-center justify-between p-3 border rounded-lg bg-background group hover:border-blue-200 transition-colors">
                <div className="flex items-center gap-3 overflow-hidden">
                   <div className="p-2 bg-red-100 rounded-lg shrink-0">
                      <FileText className="w-5 h-5 text-red-600" />
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
                {!uploading && (
                   <button
                      onClick={clearFile}
                      className="p-2 rounded-full hover:bg-red-50 text-muted-foreground hover:text-red-600 transition-colors"
                   >
                      <Trash2 className="w-4 h-4" />
                   </button>
                )}
             </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="flex justify-end gap-3 pt-2">
         <Button 
            variant="outline" 
            onClick={clearFile}
            disabled={!file || uploading}
         >
            Cancel
         </Button>
         <Button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="bg-primary hover:bg-primary/90 text-primary-foreground min-w-[100px]"
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
  )
}
