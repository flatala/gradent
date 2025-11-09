import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Calendar, TrendingUp, Target, CheckCircle2, List, FileText, Sparkles, Loader2, PlayCircle, X, RefreshCw } from "lucide-react";

interface Assignment {
  id: string;
  title: string;
  course: string;
  courseName: string;
  dueDate: string;
  weight: number;
  urgency: "high" | "medium" | "low";
  autoSelected: boolean;
  topics?: string[];
  description?: string;
  materials?: string;
}

export type ExamType = "multiple-choice" | "open-questions" | "custom";

interface AssignmentCardProps {
  assignment: Assignment;
  isGenerating?: boolean;
  hasExam?: boolean;
  onStartExam: (assignment: Assignment, examType: ExamType, customInstructions?: string) => void;
  onViewExam?: (assignment: Assignment) => void;
}

const AssignmentCard = ({ assignment, isGenerating = false, hasExam = false, onStartExam, onViewExam }: AssignmentCardProps) => {
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [showRegenerateOptions, setShowRegenerateOptions] = useState(false);
  const [customInstructions, setCustomInstructions] = useState("");

  const urgencyColors: Record<
    Assignment["urgency"],
    "destructive" | "warning" | "success"
  > = {
    high: "destructive",
    medium: "warning",
    low: "success",
  };

  const daysUntil = Math.ceil(
    (new Date(assignment.dueDate).getTime() - new Date().getTime()) /
      (1000 * 60 * 60 * 24),
  );

  const handleExamTypeClick = (examType: ExamType) => {
    if (examType === "custom") {
      setShowCustomInput(true);
    } else {
      onStartExam(assignment, examType);
    }
  };

  const handleCustomSubmit = () => {
    if (customInstructions.trim()) {
      onStartExam(assignment, "custom", customInstructions);
      setCustomInstructions("");
      setShowCustomInput(false);
    }
  };

  return (
    <Card className="p-6 bg-gradient-card border-border/50 hover:shadow-md transition-all duration-300 hover:scale-[1.02]">
      <div className="space-y-4">
        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="font-semibold text-lg leading-tight">
                {assignment.title}
              </h3>
              <p className="text-sm text-muted-foreground">
                {assignment.course}
              </p>
            </div>
            {assignment.autoSelected && (
              <Badge variant="outline" className="text-xs shrink-0">
                Auto-selected
              </Badge>
            )}
          </div>
        </div>

        {/* Details */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">
              Due in{" "}
              <span className="font-medium text-foreground">
                {daysUntil} days
              </span>
            </span>
          </div>

          <div className="flex items-center gap-2 text-sm">
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">
              Weight:{" "}
              <span className="font-medium text-foreground">
                {assignment.weight}%
              </span>
            </span>
          </div>

          <div className="flex items-center gap-2 text-sm">
            <Target className="h-4 w-4 text-muted-foreground" />
            <Badge
              variant={urgencyColors[assignment.urgency]}
              className="text-xs"
            >
              {assignment.urgency} priority
            </Badge>
          </div>
        </div>

        {/* Exam Type Selection or Status */}
        <div className="space-y-3">
          {isGenerating ? (
            <div className="flex flex-col items-center justify-center py-8 space-y-3">
              <div className="relative">
                <Loader2 className="h-12 w-12 text-primary animate-spin" />
                <Sparkles className="h-5 w-5 text-primary/60 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
              </div>
              <p className="text-sm text-muted-foreground">Generating your exam...</p>
            </div>
          ) : hasExam ? (
            <div className="flex flex-col items-center justify-center py-6 space-y-3">
              <div className="flex items-center justify-center w-16 h-16 rounded-full bg-primary/10">
                <CheckCircle2 className="h-8 w-8 text-primary" />
              </div>
              <p className="text-sm font-medium">Exam Ready!</p>
              
              {!showRegenerateOptions ? (
                <div className="w-full space-y-2">
                  <Button
                    onClick={() => onViewExam?.(assignment)}
                    className="w-full gap-2"
                  >
                    <PlayCircle className="h-4 w-4" />
                    Start Exam
                  </Button>
                  <Button
                    onClick={() => setShowRegenerateOptions(true)}
                    variant="outline"
                    className="w-full gap-2"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Regenerate Exam
                  </Button>
                </div>
              ) : (
                <div className="w-full space-y-2">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-muted-foreground">Choose exam type:</p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowRegenerateOptions(false)}
                      className="h-6 w-6 p-0"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  <Button
                    onClick={() => {
                      handleExamTypeClick("multiple-choice");
                      setShowRegenerateOptions(false);
                    }}
                    variant="outline"
                    className="w-full justify-start gap-2 hover:bg-primary/10 hover:border-primary"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="flex-1 text-left">10 Multiple Choice Questions</span>
                  </Button>
                  
                  <Button
                    onClick={() => {
                      handleExamTypeClick("open-questions");
                      setShowRegenerateOptions(false);
                    }}
                    variant="outline"
                    className="w-full justify-start gap-2 hover:bg-primary/10 hover:border-primary"
                  >
                    <FileText className="h-4 w-4" />
                    <span className="flex-1 text-left">5 Open Questions</span>
                  </Button>
                  
                  <Button
                    onClick={() => {
                      setShowRegenerateOptions(false);
                      setShowCustomInput(true);
                    }}
                    variant="outline"
                    className="w-full justify-start gap-2 hover:bg-primary/10 hover:border-primary"
                  >
                    <List className="h-4 w-4" />
                    <span className="flex-1 text-left">Custom Instructions</span>
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <>
              {!showCustomInput ? (
                <div className="grid grid-cols-1 gap-2">
                  <Button
                    onClick={() => handleExamTypeClick("multiple-choice")}
                    variant="outline"
                    className="w-full justify-start gap-2 hover:bg-primary/10 hover:border-primary"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="flex-1 text-left">10 Multiple Choice Questions</span>
                  </Button>
                  
                  <Button
                    onClick={() => handleExamTypeClick("open-questions")}
                    variant="outline"
                    className="w-full justify-start gap-2 hover:bg-primary/10 hover:border-primary"
                  >
                    <FileText className="h-4 w-4" />
                    <span className="flex-1 text-left">5 Open Questions</span>
                  </Button>
                  
                  <Button
                    onClick={() => handleExamTypeClick("custom")}
                    variant="outline"
                    className="w-full justify-start gap-2 hover:bg-primary/10 hover:border-primary"
                  >
                    <List className="h-4 w-4" />
                    <span className="flex-1 text-left">Custom Instructions</span>
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Input
                    placeholder="Enter custom exam instructions (e.g., '3 essay questions about...')"
                    value={customInstructions}
                    onChange={(e) => setCustomInstructions(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        handleCustomSubmit();
                      }
                    }}
                    className="w-full"
                    autoFocus
                  />
                  <div className="flex gap-2">
                    <Button
                      onClick={handleCustomSubmit}
                      className="flex-1"
                      disabled={!customInstructions.trim()}
                    >
                      Generate
                    </Button>
                    <Button
                      onClick={() => {
                        setShowCustomInput(false);
                        setCustomInstructions("");
                      }}
                      variant="outline"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </Card>
  );
};

export default AssignmentCard;
