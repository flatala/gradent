import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Calendar,
  BookOpen,
  Brain,
  TrendingUp,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import AssignmentCard from "./AssignmentCard";
import MockExam from "./MockExam";
import ResultsView from "./ResultsView";
import ScheduleAdjustment from "./ScheduleAdjustment";
import ConsentModal from "./ConsentModal";
import { CalendarSync } from "./CalendarSync";
import { api } from "@/lib/api";
import type { SuggestionRecord } from "@/lib/types";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";

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
  const [suggestions, setSuggestions] = useState<SuggestionRecord[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);
  const { toast } = useToast();

  const handleConnect = () => {
    setShowConsent(true);
  };

  const handleConsent = () => {
    setShowConsent(false);
    setIsConnected(true);
    setSyncStatus("syncing");
    toast({
      title: "Services connected",
      description: "We’re syncing your assignments and calendar now.",
    });

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

  const fetchSuggestions = useCallback(async () => {
    setSuggestionsLoading(true);
    setSuggestionsError(null);
    try {
      const response = await api.listSuggestions();
      setSuggestions(response.suggestions);
    } catch (err) {
      setSuggestionsError((err as Error).message);
    } finally {
      setSuggestionsLoading(false);
    }
  }, []);

  const handleGenerateSuggestions = useCallback(async () => {
    setSuggestionsLoading(true);
    setSuggestionsError(null);
    try {
      const response = await api.generateSuggestions();
      setSuggestions(response.suggestions);
    } catch (err) {
      setSuggestionsError((err as Error).message);
    } finally {
      setSuggestionsLoading(false);
    }
  }, []);

  const handleResetSuggestions = useCallback(async () => {
    setSuggestionsLoading(true);
    setSuggestionsError(null);
    try {
      await api.resetSuggestions({});
      const response = await api.listSuggestions();
      setSuggestions(response.suggestions);
    } catch (err) {
      setSuggestionsError((err as Error).message);
    } finally {
      setSuggestionsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isConnected && syncStatus === "synced") {
      fetchSuggestions();
    }
  }, [isConnected, syncStatus, fetchSuggestions]);

  useEffect(() => {
    if (syncStatus === "synced") {
      toast({
        title: "Sync complete",
        description: "Your workspace is ready with the latest data.",
      });
    }
  }, [syncStatus, toast]);

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

            <Card className="bg-gradient-card border-border/50">
              <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-xl font-semibold">Latest Suggestions</h3>
                  <p className="text-sm text-muted-foreground">
                    Personalized study recommendations from the agent.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={fetchSuggestions}
                    disabled={suggestionsLoading}
                  >
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Refresh
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleResetSuggestions}
                    disabled={suggestionsLoading}
                  >
                    Reset
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleGenerateSuggestions}
                    disabled={suggestionsLoading}
                  >
                    <Sparkles className="mr-2 h-4 w-4" />
                    Generate
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {suggestionsError && (
                  <Alert variant="destructive">
                    <AlertDescription>{suggestionsError}</AlertDescription>
                  </Alert>
                )}
                {suggestionsLoading && (
                  <>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Fetching suggestions...
                    </div>
                    <div className="space-y-3">
                      {[1, 2, 3].map((item) => (
                        <div
                          key={item}
                          className="rounded-lg border border-border/40 bg-background/60 p-4"
                        >
                          <Skeleton className="h-5 w-40 mb-2" />
                          <Skeleton className="h-4 w-full mb-2" />
                          <Skeleton className="h-4 w-3/4" />
                        </div>
                      ))}
                    </div>
                  </>
                )}
                {!suggestionsLoading && suggestions.length === 0 ? (
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <p>
                      You’re all set! As we learn more about your assignments,
                      you’ll see tailored tips here. In the meantime, try these
                      quick starters:
                    </p>
                    <ul className="list-disc space-y-1 pl-5 text-foreground/80">
                      <li>Ask the assistant to summarize your next deadline.</li>
                      <li>Log a recent study session to track progress.</li>
                      <li>
                        Generate a mock exam to review tricky course material.
                      </li>
                    </ul>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {suggestions.map((suggestion) => (
                      <div
                        key={suggestion.id}
                        className="rounded-lg border border-border/50 bg-background/60 p-4"
                      >
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <h4 className="font-semibold">{suggestion.title}</h4>
                            <p className="text-sm text-muted-foreground">
                              {suggestion.message}
                            </p>
                          </div>
                          <Badge variant="secondary">
                            {suggestion.priority?.toUpperCase() ?? "INFO"}
                          </Badge>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                          {suggestion.category && (
                            <span>Category: {suggestion.category}</span>
                          )}
                          {suggestion.status && (
                            <span>Status: {suggestion.status}</span>
                          )}
                          {suggestion.suggested_time_text && (
                            <span>
                              Suggested time: {suggestion.suggested_time_text}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <header className="flex flex-col gap-1 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold bg-gradient-primary bg-clip-text text-transparent">
            Study Autopilot
          </h1>
          <p className="text-xs text-muted-foreground">
            Keep your assignments, study blocks, and reminders aligned.
          </p>
        </div>
        {isConnected && syncStatus === "synced" && (
          <Badge className="bg-success text-success-foreground">
            <CheckCircle2 className="mr-1 h-3 w-3" /> Synced moments ago
          </Badge>
        )}
      </header>

      <div className="space-y-8 px-4 py-6">
        {isConnected && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4 animate-slide-up">
            <Card className="p-4 bg-gradient-card border-border/50">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <BookOpen className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">3</p>
                  <p className="text-sm text-muted-foreground">Active Tasks</p>
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
                  <p className="text-sm text-muted-foreground">Scheduled</p>
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
                  <p className="text-sm text-muted-foreground">Avg Score</p>
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
                  <p className="text-sm text-muted-foreground">Days Until Exam</p>
                </div>
              </div>
            </Card>
          </div>
        )}

        {renderMainContent()}
      </div>

      {showConsent && (
        <ConsentModal
          onConsent={handleConsent}
          onClose={() => setShowConsent(false)}
        />
      )}
    </>
  );
};

export default Dashboard;
