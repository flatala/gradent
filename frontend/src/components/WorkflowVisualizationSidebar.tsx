import { X, Activity, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useWorkflow } from "@/contexts/WorkflowContext";
import { ToolCallCard } from "@/components/ToolCallCard";

export const WorkflowVisualizationSidebar = () => {
  const { toolCalls, isVisible, setVisible, clearToolCalls } = useWorkflow();

  return (
    <div 
      className={`fixed right-0 top-0 h-screen w-[400px] bg-background border-l border-border shadow-2xl z-40 flex flex-col transform transition-transform duration-300 ease-in-out ${
        isVisible ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Activity className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2 className="font-semibold text-sm">Agent Activity</h2>
            <p className="text-xs text-muted-foreground">
              {toolCalls.length} agent tool call{toolCalls.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {toolCalls.length > 0 && (
            <Button
              variant="ghost"
              size="icon"
              onClick={clearToolCalls}
              className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
              title="Clear all activity"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setVisible(false)}
            className="h-8 w-8"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-3">
          {toolCalls.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="p-4 bg-muted rounded-full mb-4">
                <Activity className="h-8 w-8 text-muted-foreground" />
              </div>
              <p className="text-sm font-medium">No Agent Actions Yet</p>
              <p className="text-xs text-muted-foreground mt-1">
                Agent tool calls will appear here
              </p>
            </div>
          ) : (
            toolCalls.map((toolCall) => (
              <ToolCallCard key={toolCall.id} toolCall={toolCall} />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
};
