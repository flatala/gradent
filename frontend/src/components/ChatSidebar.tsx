import { useEffect, useState } from "react";
import { Send, Bot, Loader2 } from "lucide-react";
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
import { useWorkflow } from "@/contexts/WorkflowContext";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

type Message = { role: "user" | "assistant"; content: string };

export function ChatSidebar() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const SESSION_ID = "dashboard-assistant";
  
  const { addToolCall, completeToolCall, failToolCall, clearToolCalls } = useWorkflow();

  useEffect(() => {
    let mounted = true;
    
    // DON'T clear tool calls on mount - they're now persisted in localStorage
    // clearToolCalls();

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

    const optimisticHistory: Message[] = [...messages, { role: "user" as const, content: userText }];
    setMessages(optimisticHistory);
    setLoading(true);

    try {
      const response = await api.sendChatMessage({
        session_id: SESSION_ID,
        message: userText,
      });
      setMessages(response.history);
      
      // ONLY process tool calls if the backend actually returned some
      console.log("=== BACKEND RESPONSE ===");
      console.log("Full response:", response);
      console.log("Tool calls:", response.tool_calls);
      console.log("Tool calls type:", typeof response.tool_calls);
      console.log("Tool calls is array:", Array.isArray(response.tool_calls));
      
      if (response.tool_calls && Array.isArray(response.tool_calls) && response.tool_calls.length > 0) {
        console.log(`Processing ${response.tool_calls.length} tool calls from backend`);

        // Filter to only show completed or failed tools (ignore "started" status to avoid loading banners)
        const completedTools = response.tool_calls.filter(
          tc => tc.status === "completed" || tc.status === "failed"
        );

        console.log(`Filtered to ${completedTools.length} completed/failed tools`);

        completedTools.forEach((toolCall, index) => {
          console.log(`\n=== Tool Call ${index + 1} ===`);
          console.log("Full tool call object:", toolCall);
          console.log("Tool name:", toolCall.tool_name);
          console.log("Tool type:", toolCall.tool_type);
          console.log("Status:", toolCall.status);
          console.log("Result:", toolCall.result);
          console.log("Result type:", typeof toolCall.result);

          // Create tool call banner directly with final status
          const toolCallId = addToolCall({
            type: toolCall.tool_type,
            status: toolCall.status,
            title: toolCall.tool_name,
            description: undefined,
            result: toolCall.result,
          });

          // Show success or error toast
          if (toolCall.status === "completed" && toolCall.result) {
            console.log("Tool result:", toolCall.result);
            toast.success(toolCall.tool_name, {
              description: "Task completed successfully!",
              id: toolCallId,
            });
          } else if (toolCall.status === "failed" && toolCall.error) {
            toast.error(toolCall.tool_name, {
              description: toolCall.error,
              id: toolCallId,
            });
          }
        });
      } else {
        console.log("No tool calls in backend response");
      }
      
    } catch (err) {
      const fallback = (err as Error).message ?? "Failed to reach the assistant.";
      setMessages([
        ...optimisticHistory,
        { role: "assistant" as const, content: fallback },
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
                    ? "bg-primary"
                    : "bg-muted text-foreground"
                }`}
                style={msg.role === "user" ? { color: "#ffffff" } : {}}
              >
                <div className={`prose prose-sm max-w-none prose-p:leading-relaxed prose-pre:p-0 overflow-hidden ${
                  msg.role === "user" 
                    ? "prose-invert [&_*]:text-white" 
                    : "dark:prose-invert"
                }`}
                style={msg.role === "user" ? { color: "#ffffff" } : {}}
                >
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                    components={{
                      // Custom link rendering with truncation
                      a: ({ node, href, children, ...props }) => {
                        const url = href || '';
                        let displayText = children;
                        
                        // ALWAYS truncate long URLs aggressively
                        if (typeof children === 'string') {
                          const textContent = String(children);
                          // If it's a URL (starts with http), truncate it
                          if (textContent.startsWith('http://') || textContent.startsWith('https://')) {
                            try {
                              const urlObj = new URL(textContent);
                              const domain = urlObj.hostname.replace('www.', '');
                              
                              // For Google Meet links
                              if (domain.includes('meet.google.com')) {
                                displayText = '🎥 Join Meet';
                              } 
                              // For Google Calendar links
                              else if (domain.includes('google.com') && textContent.includes('calendar')) {
                                displayText = '📅 View Calendar';
                              }
                              // For other URLs
                              else {
                                displayText = `🔗 ${domain}`;
                              }
                            } catch {
                              // Fallback truncation
                              displayText = textContent.length > 25 ? textContent.slice(0, 25) + '...' : textContent;
                            }
                          }
                        }
                        
                        return (
                          <a
                            {...props}
                            href={href}
                            className="text-blue-500 hover:text-blue-600 underline inline-block whitespace-nowrap"
                            target="_blank"
                            rel="noopener noreferrer"
                            title={url}
                          >
                            {displayText}
                          </a>
                        );
                      },
                      // Ensure paragraphs don't overflow
                      p: ({ node, ...props }) => (
                        <p {...props} className="break-words whitespace-pre-wrap" style={{ overflowWrap: "anywhere" }} />
                      ),
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          ))}
          
          {/* Loading indicator when waiting for response */}
          {loading && (
            <div className="flex justify-start">
              <div className="max-w-[85%] p-3 rounded-lg bg-muted text-foreground">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span className="text-sm text-muted-foreground">Agenting...</span>
                </div>
              </div>
            </div>
          )}
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
                loading ? "Assistant is agenting..." : "Ask me anything..."
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
