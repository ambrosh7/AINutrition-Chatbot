import type { ChatResponse } from "../types/chat";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(
  /\/$/,
  ""
) ?? "";

async function parseError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
    return `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

export async function createConversation(): Promise<string> {
  const response = await fetch(`${API_BASE}/api/conversations`, {
    method: "POST",
  });
  if (!response.ok) throw new Error(await parseError(response));
  const data = (await response.json()) as { conversation_id: string };
  return data.conversation_id;
}

export async function sendChat(
  conversationId: string,
  message: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversation_id: conversationId,
      message,
    }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return (await response.json()) as ChatResponse;
}
