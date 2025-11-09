import { useState } from "react";
import Dashboard from "@/components/Dashboard";
import AutonomousMode from "@/components/AutonomousMode";
import { Button } from "@/components/ui/button";
import { BookOpen, Activity, Bot } from "lucide-react";
import { ChatSidebar } from "@/components/ChatSidebar";
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { WorkflowProvider, useWorkflow } from "@/contexts/WorkflowContext";
import { WorkflowVisualizationSidebar } from "@/components/WorkflowVisualizationSidebar";
import { Badge } from "@/components/ui/badge";

const IndexContent = () => {
  const [activeTab, setActiveTab] = useState<"dashboard" | "autonomous">("dashboard");
  const { toolCalls, isVisible, setVisible } = useWorkflow();

  return (
    <SidebarProvider defaultOpen={true}>
      <div className="min-h-screen flex w-full bg-gradient-to-br from-background via-background/95 to-primary/5">
        {/* Fixed toggle button in upper left corner */}
        <Tooltip delayDuration={200}>
          <TooltipTrigger asChild>
            <SidebarTrigger className="fixed top-4 left-4 z-50 h-10 w-10 rounded-full border bg-background shadow-md transition hover:bg-primary hover:text-primary-foreground" />
          </TooltipTrigger>
          <TooltipContent side="right">Toggle AI Assistant</TooltipContent>
        </Tooltip>

        <ChatSidebar />

        <SidebarInset className="flex-1" style={{ marginRight: isVisible ? '400px' : '0', transition: 'margin-right 0.3s ease' }}>
          <div className="container mx-auto px-4 pt-4 pb-8">
            {/* Header - Centered */}
            <div className="mb-6 animate-fade-in">
              {/* Tab Navigation - Space Between */}
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-6">
                  <h1 className="text-2xl font-semibold bg-gradient-primary bg-clip-text text-transparent">
                    Study Autopilot
                  </h1>
                  <div className="flex gap-3">
                    <Button
                      onClick={() => setActiveTab("dashboard")}
                      variant={activeTab === "dashboard" ? "default" : "outline"}
                      className={
                        activeTab === "dashboard" ? "bg-gradient-primary shadow-md" : ""
                      }
                    >
                      <BookOpen className="w-4 h-4 mr-2" />
                      Dashboard
                    </Button>
                    <Button
                      onClick={() => setActiveTab("autonomous")}
                      variant={activeTab === "autonomous" ? "default" : "outline"}
                      className={
                        activeTab === "autonomous" ? "bg-gradient-primary shadow-md" : ""
                      }
                    >
                      <Bot className="w-4 h-4 mr-2" />
                      Autonomous Mode
                    </Button>
                  </div>
                </div>
                
                <Button
                  variant={isVisible ? "default" : "outline"}
                  onClick={() => setVisible(!isVisible)}
                  className="gap-2 relative"
                  size="sm"
                >
                  <Activity className="h-4 w-4" />
                  Agent Activity
                  {toolCalls.length > 0 && (
                    <Badge 
                      variant="secondary" 
                      className="ml-1 h-5 min-w-[1.25rem] px-1 flex items-center justify-center"
                    >
                      {toolCalls.length}
                    </Badge>
                  )}
                </Button>
              </div>
            </div>

            {/* Content */}
            {activeTab === "dashboard" && <Dashboard />}
            {activeTab === "autonomous" && <AutonomousMode />}
          </div>
        </SidebarInset>

        {/* Workflow Visualization Sidebar */}
        <WorkflowVisualizationSidebar />
      </div>
    </SidebarProvider>
  );
};

const Index = () => {
  return (
    <WorkflowProvider>
      <IndexContent />
    </WorkflowProvider>
  );
};

export default Index;
