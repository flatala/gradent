import React, { createContext, useContext, useState, useCallback } from "react";

export type ToolCallType = "scheduler" | "assessment" | "suggestions" | "exam_generation";
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

export const WorkflowProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toolCalls, setToolCalls] = useState<ToolCallVisualization[]>([]);
  const [isVisible, setIsVisible] = useState(false);

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
