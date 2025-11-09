import { useState } from "react";
import Dashboard from "@/components/Dashboard";
import ExamGenerator from "@/components/ExamGenerator";
import { Button } from "@/components/ui/button";
import { BookOpen, Brain } from "lucide-react";
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

const Index = () => {
  const [activeTab, setActiveTab] = useState<"dashboard" | "exam">("dashboard");

  return (
    <SidebarProvider defaultOpen>
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>
          <SidebarTrigger className="fixed top-4 left-4 z-40 hidden h-10 w-10 items-center justify-center rounded-full border bg-background shadow-md transition hover:bg-primary hover:text-primary-foreground lg:flex" />
        </TooltipTrigger>
        <TooltipContent side="right">Toggle assistant</TooltipContent>
      </Tooltip>

      <div className="flex min-h-screen bg-gradient-to-br from-background via-background/95 to-primary/5">
        <ChatSidebar />

        <SidebarInset className="flex-1">
          <div className="container mx-auto px-4 py-8">
            {/* Header - Centered */}
            <div className="mb-8 animate-fade-in">
              <div className="lg:hidden mb-4">
                <SidebarTrigger className="inline-flex h-10 w-10 items-center justify-center rounded-full border bg-background shadow-sm hover:bg-primary hover:text-primary-foreground" />
              </div>
              <div className="flex flex-col items-center justify-center text-center mb-6 space-y-2">
                <div className="w-16 h-16 bg-gradient-primary rounded-2xl flex items-center justify-center shadow-glow animate-pulse-glow mb-4">
                  <Brain className="w-8 h-8 text-white" />
                </div>
                <h1 className="text-5xl font-bold bg-gradient-to-r from-primary via-primary/80 to-accent bg-clip-text text-transparent md:text-6xl">
                  GradEnt AI
                </h1>
                <p className="text-base text-muted-foreground md:text-lg">
                  Your intelligent study companion
                </p>
                <p className="max-w-2xl text-sm text-muted-foreground/80 md:text-base">
                  Sync assignments, schedule focused work blocks, and get proactive guidance from your AI assistant—all in one place.
                </p>
              </div>

              {/* Tab Navigation - Left Aligned */}
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
                  onClick={() => setActiveTab("exam")}
                  variant={activeTab === "exam" ? "default" : "outline"}
                  className={
                    activeTab === "exam" ? "bg-gradient-primary shadow-md" : ""
                  }
                >
                  <Brain className="w-4 h-4 mr-2" />
                  Exam Generator
                </Button>
              </div>
            </div>

            {/* Content */}
            {activeTab === "dashboard" ? <Dashboard /> : <ExamGenerator />}
          </div>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default Index;
