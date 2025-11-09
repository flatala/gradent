import { Calendar, Brain, Lightbulb, FileText, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

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

interface ToolCallCardProps {
  toolCall: ToolCallVisualization;
}

export const ToolCallCard = ({ toolCall }: ToolCallCardProps) => {
  const getIcon = () => {
    switch (toolCall.type) {
      case "scheduler":
        return Calendar;
      case "assessment":
        return FileText;
      case "suggestions":
        return Lightbulb;
      case "exam_generation":
        return Brain;
    }
  };

  const getColor = () => {
    switch (toolCall.status) {
      case "completed":
        return "text-success bg-success/10 border-success/30";
      case "in_progress":
        return "text-primary bg-primary/10 border-primary/30";
      case "failed":
        return "text-destructive bg-destructive/10 border-destructive/30";
      case "pending":
        return "text-muted-foreground bg-muted border-muted-foreground/30";
    }
  };

  const getStatusIcon = () => {
    switch (toolCall.status) {
      case "completed":
        return <CheckCircle2 className="h-4 w-4" />;
      case "in_progress":
        return <Loader2 className="h-4 w-4 animate-spin" />;
      case "failed":
        return <XCircle className="h-4 w-4" />;
      case "pending":
        return <Loader2 className="h-4 w-4" />;
    }
  };

  const Icon = getIcon();

  return (
    <Card className={`border-2 ${getColor()} transition-all duration-300`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-background/50">
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-sm font-semibold">{toolCall.title}</CardTitle>
              {toolCall.description && (
                <p className="text-xs text-muted-foreground mt-0.5">{toolCall.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {getStatusIcon()}
            <Badge variant="outline" className="text-xs capitalize">
              {toolCall.status}
            </Badge>
          </div>
        </div>
      </CardHeader>

      {/* Result Content */}
      {toolCall.status === "completed" && toolCall.result && (
        <CardContent className="pt-0">
          {toolCall.type === "scheduler" && (
            <SchedulerResult result={toolCall.result} />
          )}
          {toolCall.type === "assessment" && (
            <AssessmentResult result={toolCall.result} />
          )}
          {toolCall.type === "suggestions" && (
            <SuggestionsResult result={toolCall.result} />
          )}
          {toolCall.type === "exam_generation" && (
            <ExamResult result={toolCall.result} />
          )}
        </CardContent>
      )}

      {/* Error Content */}
      {toolCall.status === "failed" && toolCall.error && (
        <CardContent className="pt-0">
          <div className="text-xs text-destructive bg-destructive/10 p-3 rounded-md">
            {toolCall.error}
          </div>
        </CardContent>
      )}

      {/* Loading Content */}
      {toolCall.status === "in_progress" && (
        <CardContent className="pt-0">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            Processing...
          </div>
        </CardContent>
      )}
    </Card>
  );
};

// Result component for scheduler
const SchedulerResult = ({ result }: { result: any }) => (
  <div className="space-y-2">
    <div className="flex items-start gap-2">
      <Calendar className="h-4 w-4 text-muted-foreground mt-0.5" />
      <div className="flex-1">
        <p className="text-sm font-medium">{result.meeting_name || result.title}</p>
        {result.start_time && (
          <p className="text-xs text-muted-foreground">
            {new Date(result.start_time).toLocaleString()}
          </p>
        )}
        {result.duration_minutes && (
          <p className="text-xs text-muted-foreground">{result.duration_minutes} minutes</p>
        )}
      </div>
    </div>
    {result.attendee_emails && result.attendee_emails.length > 0 && (
      <div className="text-xs text-muted-foreground">
        Attendees: {result.attendee_emails.join(", ")}
      </div>
    )}
    {result.event_link && (
      <Button
        variant="outline"
        size="sm"
        className="w-full mt-2"
        onClick={() => window.open(result.event_link, "_blank")}
      >
        Open in Calendar
      </Button>
    )}
  </div>
);

// Result component for assessment
const AssessmentResult = ({ result }: { result: any }) => (
  <div className="space-y-2">
    {result.effort_estimates && (
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">Effort Estimate:</span>
        <span className="font-medium">
          {result.effort_estimates.most_likely_hours || result.effort_estimates.effort_hours_most} hours
        </span>
      </div>
    )}
    {result.difficulty_1to5 && (
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">Difficulty:</span>
        <span className="font-medium">{result.difficulty_1to5}/5</span>
      </div>
    )}
    {result.risk_score_0to100 !== undefined && (
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">Risk Score:</span>
        <Badge variant={result.risk_score_0to100 > 70 ? "destructive" : "secondary"}>
          {result.risk_score_0to100}/100
        </Badge>
      </div>
    )}
    {result.milestones && result.milestones.length > 0 && (
      <div className="mt-2">
        <p className="text-xs font-medium mb-1">Milestones:</p>
        <ul className="text-xs space-y-1">
          {result.milestones.slice(0, 3).map((milestone: any, idx: number) => (
            <li key={idx} className="text-muted-foreground">
              • {typeof milestone === "string" ? milestone : milestone.title || milestone.name}
            </li>
          ))}
          {result.milestones.length > 3 && (
            <li className="text-muted-foreground italic">
              +{result.milestones.length - 3} more...
            </li>
          )}
        </ul>
      </div>
    )}
  </div>
);

// Result component for suggestions
const SuggestionsResult = ({ result }: { result: any }) => {
  const suggestions = result.suggestions || result.items || [];
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Generated {suggestions.length} suggestion{suggestions.length !== 1 ? "s" : ""}
      </p>
      {suggestions.slice(0, 3).map((suggestion: any, idx: number) => (
        <div key={idx} className="text-xs p-2 bg-muted/50 rounded">
          <p className="font-medium">{suggestion.title || suggestion.message}</p>
          {suggestion.message && suggestion.title && (
            <p className="text-muted-foreground mt-0.5">{suggestion.message}</p>
          )}
        </div>
      ))}
      {suggestions.length > 3 && (
        <p className="text-xs text-muted-foreground italic">
          +{suggestions.length - 3} more suggestions
        </p>
      )}
    </div>
  );
};

// Result component for exam generation
const ExamResult = ({ result }: { result: any }) => (
  <div className="space-y-2">
    <div className="flex items-center justify-between text-xs">
      <span className="text-muted-foreground">Questions Generated:</span>
      <span className="font-medium">{result.questions_count || result.total_questions || "N/A"}</span>
    </div>
    {result.files_processed && (
      <div className="text-xs text-muted-foreground">
        Processed {result.files_processed.length} file{result.files_processed.length !== 1 ? "s" : ""}
      </div>
    )}
    {result.exam_file && (
      <Button
        variant="outline"
        size="sm"
        className="w-full mt-2"
        onClick={() => window.open(result.exam_file, "_blank")}
      >
        Download Exam
      </Button>
    )}
  </div>
);

