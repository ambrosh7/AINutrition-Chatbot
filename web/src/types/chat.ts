export type Claim = {
  text: string;
  source: null | string | Record<string, unknown>;
};

export type ChatMeta = {
  conversation_id: string;
  message_id: string;
  declined: boolean;
  decline_reason: string | null;
};

export type ChatResponse = {
  answer: string;
  claims: Claim[];
  meta: ChatMeta;
};

export type ChatTurn = {
  id: string;
  role: "user" | "assistant";
  content: string;
  declined?: boolean;
  claims?: Claim[];
};
