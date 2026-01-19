"use client";

import * as React from "react";
import { useChat } from "@ai-sdk/react";
import type { UIMessage } from "ai";
import { Loader2, Send, Square } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

function messageText(message: UIMessage): string {
  return (message.parts || [])
    .filter(
      (p): p is { type: "text"; text: string } => (p as any)?.type === "text",
    )
    .map((p) => p.text)
    .join("");
}

export function Chat({
  title = "Financial advice",
  description = "Ask anything about your spending, subscriptions, goals, or cash flow.",
  quickActions = [
    "💸 What are my biggest expenses this month?",
    "🧾 Do I have any subscriptions I should cancel?",
    "📊 Where did my money go last week?",
    "🔁 What recurring charges increased recently?",
    "🎯 Am I on track for my savings goals?",
  ],
}: {
  title?: string;
  description?: string;
  quickActions?: string[];
}) {
  const { messages, sendMessage, status, error, stop, clearError } = useChat();
  const [input, setInput] = React.useState("");
  const endRef = React.useRef<HTMLDivElement | null>(null);
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);

  React.useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, status]);

  const isBusy = status === "submitted" || status === "streaming";
  const showQuickActions = quickActions.length > 0 && input.trim().length === 0;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || isBusy) return;
    setInput("");
    await sendMessage({ text });
  }

  return (
    <Card className="min-w-0">
      <CardHeader className="gap-1">
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>

      <CardContent className="min-w-0">
        {error ? (
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm">
            <div className="font-medium">Something went wrong</div>
            <div className="text-muted-foreground mt-1 wrap-break-word">
              {error.message}
            </div>
            <div className="mt-3 flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  clearError();
                }}
              >
                Dismiss
              </Button>
            </div>
          </div>
        ) : null}

        <div className="mt-4 flex h-[55vh] min-h-[320px] flex-col gap-3 overflow-y-auto">
          {messages.map((m) => {
            const text = messageText(m);
            if (!text) return null;

            const isUser = m.role === "user";
            return (
              <div
                key={m.id}
                className={cn("flex", isUser ? "justify-end" : "justify-start")}
              >
                <div
                  className={cn(
                    "max-w-[85%] rounded-2xl px-4 py-2 text-sm leading-relaxed shadow-sm",
                    isUser
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground border border-border",
                  )}
                >
                  <div className="whitespace-pre-wrap wrap-break-word">
                    {text}
                  </div>
                </div>
              </div>
            );
          })}

          {isBusy ? (
            <div className="flex justify-start">
              <div className="bg-muted text-muted-foreground border border-border inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Thinking…</span>
              </div>
            </div>
          ) : null}

          <div ref={endRef} />
        </div>
      </CardContent>

      <CardFooter className="flex-col items-stretch gap-2">
        {showQuickActions ? (
          <div className="flex flex-wrap gap-2">
            {quickActions.map((q) => (
              <Button
                key={q}
                type="button"
                variant="secondary"
                size="sm"
                className="h-auto rounded-full border border-border px-3 py-1.5 text-xs font-normal"
                disabled={isBusy}
                onClick={() => {
                  setInput(q);
                  requestAnimationFrame(() => {
                    textareaRef.current?.focus();
                    const len = textareaRef.current?.value?.length ?? 0;
                    textareaRef.current?.setSelectionRange(len, len);
                  });
                }}
              >
                {q}
              </Button>
            ))}
          </div>
        ) : null}

        <form onSubmit={onSubmit} className="flex w-full items-end gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Claire…"
            className="min-h-[44px] resize-none"
            disabled={status === "streaming" || status === "submitted"}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void onSubmit(e as unknown as React.FormEvent);
              }
            }}
          />

          {isBusy ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => stop()}
              className="h-[44px] shrink-0"
            >
              <Square className="h-4 w-4" />
              Stop
            </Button>
          ) : (
            <Button
              type="submit"
              className="h-[44px] shrink-0"
              disabled={!input.trim()}
            >
              <Send className="h-4 w-4" />
              Send
            </Button>
          )}
        </form>
      </CardFooter>
    </Card>
  );
}
