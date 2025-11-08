import { useState } from "react";
import Dashboard from "@/components/Dashboard";
import ExamGenerator from "@/components/ExamGenerator";
import { Button } from "@/components/ui/button";
import { BookOpen, Brain } from "lucide-react";

const Index = () => {
  const [activeTab, setActiveTab] = useState<"dashboard" | "exam">("dashboard");

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background/95 to-primary/5">
      <div className="container mx-auto px-4 py-8">
        {/* Header - Centered */}
        <div className="mb-8 animate-fade-in">
          <div className="flex flex-col items-center justify-center text-center mb-6">
            <div className="w-16 h-16 bg-gradient-primary rounded-2xl flex items-center justify-center shadow-glow animate-pulse-glow mb-4">
              <Brain className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-primary via-primary/80 to-accent bg-clip-text text-transparent">
              GradEnt AI
            </h1>
            <p className="text-muted-foreground">
              Your intelligent study companion
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
    </div>
  );
};

export default Index;
