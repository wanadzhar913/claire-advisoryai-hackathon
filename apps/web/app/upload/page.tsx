"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { UploadForm } from "@/components/UploadForm"

export default function UploadPage() {
  const router = useRouter()
  const [phase, setPhase] = React.useState<"idle" | "processing">("idle")
  const [fileName, setFileName] = React.useState("")

  const getApiUrl = () => process.env.NEXT_PUBLIC_API_URL ?? ""

  const handleSuccess = (name: string) => {
    setFileName(name)
    setPhase("processing")
    // Redirect to dashboard after showing processing message briefly
    setTimeout(() => {
      router.push("/dashboard")
    }, 2000)
  }

  return (
    <main className="min-h-screen w-full flex items-center justify-center p-4 bg-background">
      <div className="w-full max-w-2xl mx-auto flex flex-col items-center transition-all duration-500 ease-in-out">
        {phase === "idle" ? (
          <div className="w-full flex justify-center animate-in fade-in zoom-in-95 duration-500">
            <UploadForm 
              apiUrl={getApiUrl()} 
              onSuccess={handleSuccess} 
            />
          </div>
        ) : (
          <div className="text-center space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="inline-flex items-center justify-center p-4 rounded-full bg-primary/5 mb-4">
              <div className="w-3 h-3 bg-primary rounded-full animate-ping" />
            </div>
            
            <div className="space-y-2">
              <h2 className="text-2xl font-medium tracking-tight">Processing Document</h2>
              <p className="text-muted-foreground">
                Upload received. Processing statement:
              </p>
              <div className="mt-4 inline-block px-4 py-1.5 rounded-full bg-muted border font-mono text-sm text-foreground">
                {fileName}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
