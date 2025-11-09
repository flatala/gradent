import React, { createContext, useContext, useState, useCallback, useEffect } from "react";

export type ToolCallType = "scheduler" | "assessment" | "suggestions" | "exam_generation" | "progress_tracking" | "context_update";
export type ToolCallStatus = "pending" | "in_progress" | "completed" | "failed";

export interface ToolCallVisualization {
  id: string;
  type: ToolCallType;
  status: ToolCallStatus;
  timestamp: Date;
  title: string;
  description?: string;
  result?: any;
  error?: string;
}

type WorkflowContextType = {
  toolCalls: ToolCallVisualization[];
  isVisible: boolean;
  addToolCall: (toolCall: Omit<ToolCallVisualization, "id" | "timestamp">) => string;
  updateToolCall: (id: string, updates: Partial<ToolCallVisualization>) => void;
  completeToolCall: (id: string, result: any) => void;
  failToolCall: (id: string, error: string) => void;
  setVisible: (visible: boolean) => void;
  clearToolCalls: () => void;
};

const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

const STORAGE_KEY = "gradent_agent_activity";
const SESSION_KEY = "dashboard-assistant"; // Match the session ID from ChatSidebar

// Helper to load tool calls from localStorage
const loadToolCallsFromStorage = (): ToolCallVisualization[] => {
  try {
    const stored = localStorage.getItem(`${STORAGE_KEY}_${SESSION_KEY}`);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Convert timestamp strings back to Date objects
      return parsed.map((tc: any) => ({
        ...tc,
        timestamp: new Date(tc.timestamp),
      }));
    }
  } catch (error) {
    console.error("Failed to load agent activity from storage:", error);
  }
  return [];
};

// Helper to save tool calls to localStorage
const saveToolCallsToStorage = (toolCalls: ToolCallVisualization[]) => {
  try {
    localStorage.setItem(`${STORAGE_KEY}_${SESSION_KEY}`, JSON.stringify(toolCalls));
  } catch (error) {
    console.error("Failed to save agent activity to storage:", error);
  }
};

export const WorkflowProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toolCalls, setToolCalls] = useState<ToolCallVisualization[]>(() => {
    // Initialize from localStorage on mount
    return loadToolCallsFromStorage();
  });
  const [isVisible, setIsVisible] = useState(false);

  // Persist to localStorage whenever toolCalls changes
  useEffect(() => {
    saveToolCallsToStorage(toolCalls);
  }, [toolCalls]);

  const addToolCall = useCallback((toolCall: Omit<ToolCallVisualization, "id" | "timestamp">) => {
    const id = `tool-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const newToolCall: ToolCallVisualization = {
      ...toolCall,
      id,
      timestamp: new Date(),
    };
    setToolCalls(prev => [...prev, newToolCall]);
    setIsVisible(true);
    return id;
  }, []);

  const updateToolCall = useCallback((id: string, updates: Partial<ToolCallVisualization>) => {
    setToolCalls(prev => prev.map(tc => 
      tc.id === id ? { ...tc, ...updates } : tc
    ));
  }, []);

  const completeToolCall = useCallback((id: string, result: any) => {
    setToolCalls(prev => prev.map(tc =>
      tc.id === id 
        ? { ...tc, status: "completed" as const, result }
        : tc
    ));
  }, []);

  const failToolCall = useCallback((id: string, error: string) => {
    setToolCalls(prev => prev.map(tc =>
      tc.id === id 
        ? { ...tc, status: "failed" as const, error }
        : tc
    ));
  }, []);

  const setVisible = useCallback((visible: boolean) => {
    setIsVisible(visible);
  }, []);

  const clearToolCalls = useCallback(() => {
    setToolCalls([]);
  }, []);

  return (
    <WorkflowContext.Provider
      value={{
        toolCalls,
        isVisible,
        addToolCall,
        updateToolCall,
        completeToolCall,
        failToolCall,
        setVisible,
        clearToolCalls,
      }}
    >
      {children}
    </WorkflowContext.Provider>
  );
};

export const useWorkflow = () => {
  const context = useContext(WorkflowContext);
  if (!context) {
    throw new Error("useWorkflow must be used within WorkflowProvider");
  }
  return context;
};
