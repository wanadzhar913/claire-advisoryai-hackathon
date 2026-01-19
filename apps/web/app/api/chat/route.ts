import { auth, currentUser } from "@clerk/nextjs/server";
import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  type UIMessage,
} from "ai";

type BackendStreamEvent = { content: string; done: boolean };

function getBackendBaseUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.API_BASE_URL;
  if (!url) {
    throw new Error(
      "Missing backend base URL. Set NEXT_PUBLIC_API_BASE_URL (or API_BASE_URL) to e.g. http://localhost:8000",
    );
  }
  return url.replace(/\/$/, "");
}

function extractText(message: UIMessage): string {
  // We only forward plain text history to FastAPI (backend owns tools + system prompt).
  return (message.parts || [])
    .filter(
      (p): p is { type: "text"; text: string } => (p as any)?.type === "text",
    )
    .map((p) => p.text)
    .join("");
}

function toBackendMessages(
  messages: UIMessage[],
): Array<{ role: "user" | "assistant" | "system"; content: string }> {
  return (messages || [])
    .map((m) => ({ role: m.role, content: extractText(m).trim() }))
    .filter((m) => m.content.length > 0);
}

function getCookieValue(
  cookieHeader: string | null,
  name: string,
): string | null {
  if (!cookieHeader) return null;
  const parts = cookieHeader.split(";").map((c) => c.trim());
  for (const part of parts) {
    if (part.startsWith(`${name}=`)) {
      return part.slice(name.length + 1);
    }
  }
  return null;
}

async function* parseBackendSse(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<BackendStreamEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // FastAPI yields events separated by \n\n
    while (true) {
      const idx = buffer.indexOf("\n\n");
      if (idx === -1) break;
      const rawEvent = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);

      // Parse SSE "data: ..." lines
      const dataLines = rawEvent
        .split("\n")
        .map((l) => l.trim())
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.replace(/^data:\s?/, ""));

      if (dataLines.length === 0) continue;

      const dataStr = dataLines.join("\n");
      try {
        const evt = JSON.parse(dataStr) as BackendStreamEvent;
        if (
          typeof evt?.content === "string" &&
          typeof evt?.done === "boolean"
        ) {
          yield evt;
        }
      } catch {
        // Ignore malformed events; keep streaming.
      }
    }
  }
}

export async function POST(req: Request): Promise<Response> {
  const payload = (await req.json().catch(() => null)) as {
    messages?: UIMessage[];
  } | null;
  const messages = payload?.messages ?? [];

  const { userId, getToken } = await auth();
  const token = (await getToken()) ?? undefined;

  const clerkUser = await currentUser().catch(() => null);
  const primaryEmail =
    clerkUser?.emailAddresses?.find(
      (e) => e.id === clerkUser.primaryEmailAddressId,
    )?.emailAddress ??
    clerkUser?.emailAddresses?.[0]?.emailAddress ??
    undefined;

  const cookieHeader = req.headers.get("cookie");
  const demoCookie = getCookieValue(cookieHeader, "demo_mode");
  const demoMode = demoCookie === "1";

  const backendUrl = `${getBackendBaseUrl()}/api/v1/chatbot/chat/stream`;
  const backendRes = await fetch(backendUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(userId ? { "X-Clerk-User-Id": userId } : {}),
      ...(primaryEmail ? { "X-Clerk-User-Email": primaryEmail } : {}),
      ...(demoMode ? { "X-Demo-Mode": "true" } : {}),
    },
    body: JSON.stringify({ messages: toBackendMessages(messages) }),
  });

  if (!backendRes.ok) {
    const text = await backendRes.text().catch(() => "");
    return new Response(text || `Backend error (${backendRes.status})`, {
      status: 502,
    });
  }

  if (!backendRes.body) {
    return new Response("Backend returned an empty stream.", { status: 502 });
  }

  const stream = createUIMessageStream<UIMessage>({
    originalMessages: messages,
    execute: async ({ writer }) => {
      const textId = "assistant-text";
      writer.write({ type: "text-start", id: textId });

      for await (const evt of parseBackendSse(backendRes.body!)) {
        if (evt.done) break;
        if (evt.content) {
          writer.write({ type: "text-delta", id: textId, delta: evt.content });
        }
      }

      writer.write({ type: "text-end", id: textId });
    },
  });

  return createUIMessageStreamResponse({ stream });
}
