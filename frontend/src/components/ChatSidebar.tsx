import { useEffect, useState } from "react";
import { Send, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { api } from "@/lib/api";

type Message = { role: "user" | "assistant"; content: string };

export function ChatSidebar() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const SESSION_ID = "dashboard-assistant";

  useEffect(() => {
    let mounted = true;

    const bootstrap = async () => {
      try {
        const history = await api.getChatHistory(SESSION_ID);
        if (!mounted) return;
        if (history.history.length > 0) {
          setMessages(history.history);
        } else {
          setMessages([
            {
              role: "assistant",
              content:
                "Hi! I'm your Study Autopilot AI. I can help you manage your study schedule, take mock exams, and optimize your learning. What would you like to do?",
            },
          ]);
        }
      } catch {
        if (!mounted) return;
        setMessages([
          {
            role: "assistant",
            content:
              "Hi! I'm your Study Autopilot AI. I can help you manage your study schedule, take mock exams, and optimize your learning. What would you like to do?",
          },
        ]);
      }
    };

    bootstrap();

    return () => {
      mounted = false;
    };
  }, [SESSION_ID]);

  const handleSend = async () => {
    if (!message.trim() || loading) return;

    const userText = message.trim();
    setMessage("");
    setError(null);

    const optimisticHistory = [...messages, { role: "user", content: userText }];
    setMessages(optimisticHistory);
    setLoading(true);

    try {
      const response = await api.sendChatMessage({
        session_id: SESSION_ID,
        message: userText,
      });
      setMessages(response.history);
    } catch (err) {
      const fallback = (err as Error).message ?? "Failed to reach the assistant.";
      setMessages([
        ...optimisticHistory,
        { role: "assistant", content: fallback },
      ]);
      setError(fallback);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Sidebar className="border-r border-border">
      <SidebarHeader className="border-b border-border p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Bot className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="font-semibold text-sm">AI Assistant</h2>
              <p className="text-xs text-muted-foreground">
                Always here to help
              </p>
            </div>
          </div>
          <SidebarTrigger />
        </div>
      </SidebarHeader>

      <SidebarContent className="p-4">
        <div className="space-y-4">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] p-3 rounded-lg ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-foreground"
                }`}
              >
                <p className="text-sm leading-relaxed">{msg.content}</p>
              </div>
            </div>
          ))}
        </div>
      </SidebarContent>

      <SidebarFooter className="p-4 border-t border-border">
        <div className="space-y-2">
          {error && (
            <div className="text-xs text-destructive">{error}</div>
          )}
          <div className="flex gap-2">
            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !loading) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder={
                loading ? "Assistant is thinking..." : "Ask me anything..."
              }
              className="min-h-[80px] resize-none"
              disabled={loading}
            />
            <Button
              onClick={handleSend}
              size="icon"
              className="shrink-0 h-[80px]"
              disabled={loading}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
