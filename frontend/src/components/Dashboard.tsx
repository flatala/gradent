import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Calendar,
  BookOpen,
  Brain,
  TrendingUp,
  CheckCircle2,
} from "lucide-react";
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { ChatSidebar } from "./ChatSidebar";
import AssignmentCard from "./AssignmentCard";
import MockExam from "./MockExam";
import ResultsView from "./ResultsView";
import ScheduleAdjustment from "./ScheduleAdjustment";
import ConsentModal from "./ConsentModal";
import { CalendarSync } from "./CalendarSync";

const mockAssignments: Array<{
  id: string;
  title: string;
  course: string;
  dueDate: string;
  weight: number;
  urgency: "high" | "medium" | "low";
  autoSelected: boolean;
  topics: string[];
}> = [
  {
    id: "1",
    title: "Linear Algebra Midterm",
    course: "MATH 2040",
    dueDate: "2025-11-15",
    weight: 25,
    urgency: "high",
    autoSelected: true,
    topics: ["Eigenvalues", "Matrix Operations", "Vector Spaces"],
  },
  {
    id: "2",
    title: "Psychology Essay",
    course: "PSYCH 101",
    dueDate: "2025-11-18",
    weight: 15,
    urgency: "medium",
    autoSelected: false,
    topics: ["Cognitive Psychology", "Research Methods"],
  },
  {
    id: "3",
    title: "Data Structures Final Project",
    course: "CS 2402",
    dueDate: "2025-11-22",
    weight: 30,
    urgency: "medium",
    autoSelected: true,
    topics: ["Binary Trees", "Graph Algorithms", "Hash Tables"],
  },
];

const Dashboard = () => {
  const [showConsent, setShowConsent] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [currentView, setCurrentView] = useState<
    "dashboard" | "exam" | "results" | "schedule" | "calendar"
  >("dashboard");
  const [syncStatus, setSyncStatus] = useState<"idle" | "syncing" | "synced">(
    "idle",
  );
  const [selectedAssignment, setSelectedAssignment] = useState(
    mockAssignments[0],
  );
  const [examResults, setExamResults] = useState<any>(null);

  const handleConnect = () => {
    setShowConsent(true);
  };

  const handleConsent = () => {
    setShowConsent(false);
    setIsConnected(true);
    setSyncStatus("syncing");

    setTimeout(() => {
      setSyncStatus("synced");
    }, 3000);
  };

  const handleStartExam = (assignment: any) => {
    setSelectedAssignment(assignment);
    setCurrentView("exam");
  };

  const handleExamComplete = (results: any) => {
    setExamResults(results);
    setCurrentView("results");
  };

  const handleViewSchedule = () => {
    setCurrentView("schedule");
  };

  const handleBackToDashboard = () => {
    setCurrentView("dashboard");
  };

  const renderMainContent = () => {
    if (currentView === "exam") {
      return (
        <MockExam
          assignment={selectedAssignment}
          onComplete={handleExamComplete}
        />
      );
    }

    if (currentView === "results") {
      return (
        <ResultsView
          results={examResults}
          onViewSchedule={handleViewSchedule}
          onBack={handleBackToDashboard}
        />
      );
    }

    if (currentView === "schedule") {
      return (
        <ScheduleAdjustment
          results={examResults}
          onBack={handleBackToDashboard}
        />
      );
    }

    if (currentView === "calendar") {
      return <CalendarSync />;
    }

    return (
      <div className="space-y-8">
        {!isConnected && (
          <div className="flex items-center justify-center min-h-[400px]">
            <Card className="p-8 max-w-md text-center bg-gradient-card shadow-lg">
              <div className="mb-6">
                <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Brain className="h-8 w-8 text-primary" />
                </div>
                <h2 className="text-2xl font-bold mb-2">Get Started</h2>
                <p className="text-muted-foreground">
                  Connect your Brightspace and Google Calendar to let Study
                  Autopilot manage your study workflow automatically.
                </p>
              </div>
              <Button
                onClick={handleConnect}
                size="lg"
                className="w-full shadow-md"
              >
                Connect Services
              </Button>
            </Card>
          </div>
        )}

        {isConnected && (
          <div className="space-y-6 animate-fade-in">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold">Upcoming Assignments</h2>
              <Button
                variant="outline"
                onClick={() => setCurrentView("calendar")}
                className="gap-2"
              >
                <Calendar className="h-4 w-4" />
                View Calendar
              </Button>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {mockAssignments.map((assignment) => (
                <AssignmentCard
                  key={assignment.id}
                  assignment={assignment}
                  onStartExam={handleStartExam}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <SidebarProvider defaultOpen={true}>
      <div className="min-h-screen flex w-full bg-background">
        <ChatSidebar />

        <SidebarInset className="flex-1">
          <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4">
            <SidebarTrigger />
            <div className="flex-1">
              <h1 className="text-lg font-semibold bg-gradient-primary bg-clip-text text-transparent">
                Study Autopilot
              </h1>
            </div>
            {isConnected && syncStatus === "synced" && (
              <Badge className="bg-success text-success-foreground">
                <CheckCircle2 className="mr-1 h-3 w-3" />4 items synced • 2m ago
              </Badge>
            )}
          </header>

          <div className="flex-1 p-6">
            <div className="max-w-7xl mx-auto">
              {/* Stats Overview */}
              {isConnected && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8 animate-slide-up">
                  <Card className="p-4 bg-gradient-card border-border/50">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <BookOpen className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">3</p>
                        <p className="text-sm text-muted-foreground">
                          Active Tasks
                        </p>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4 bg-gradient-card border-border/50">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-accent/10">
                        <Brain className="h-5 w-5 text-accent" />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">12h</p>
                        <p className="text-sm text-muted-foreground">
                          Scheduled
                        </p>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4 bg-gradient-card border-border/50">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-success/10">
                        <TrendingUp className="h-5 w-5 text-success" />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">87%</p>
                        <p className="text-sm text-muted-foreground">
                          Avg Score
                        </p>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4 bg-gradient-card border-border/50">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-warning/10">
                        <Calendar className="h-5 w-5 text-warning" />
                      </div>
                      <div>
                        <p className="text-2xl font-bold">5</p>
                        <p className="text-sm text-muted-foreground">
                          Days Until Exam
                        </p>
                      </div>
                    </div>
                  </Card>
                </div>
              )}

              {/* Main Content */}
              {renderMainContent()}
            </div>
          </div>

          {/* Modals */}
          {showConsent && (
            <ConsentModal
              onConsent={handleConsent}
              onClose={() => setShowConsent(false)}
            />
          )}
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default Dashboard;
