import { Calendar, Brain, Lightbulb, FileText, Loader2, CheckCircle2, XCircle, TrendingUp, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

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
      case "progress_tracking":
        return TrendingUp;
      case "context_update":
        return RefreshCw;
      default:
        return Brain;
    }
  };

  const getColor = () => {
    switch (toolCall.status) {
      case "completed":
        return "text-success bg-success/10 border-success/30";
      case "in_progress":
        return "text-primary bg-primary/10 border-primary/30 animate-pulse";
      case "failed":
        return "text-destructive bg-destructive/10 border-destructive/30";
      case "pending":
        return "text-muted-foreground bg-muted border-muted-foreground/30";
    }
  };

  const getStatusIcon = () => {
    switch (toolCall.status) {
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-success" />;
      case "in_progress":
        return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-destructive" />;
      case "pending":
        return <Loader2 className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const Icon = getIcon();

  return (
    <Card className={`border-2 ${getColor()} transition-all duration-300`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`p-2 rounded-lg ${toolCall.status === 'in_progress' ? 'bg-primary/20' : 'bg-background/50'}`}>
              <Icon className={`h-5 w-5 ${toolCall.status === 'in_progress' ? 'animate-pulse' : ''}`} />
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
              {toolCall.status.replace('_', ' ')}
            </Badge>
          </div>
        </div>
      </CardHeader>

      {/* In-Progress State - Show loading skeleton */}
      {toolCall.status === "in_progress" && (
        <CardContent className="pt-0">
          <div className="space-y-3 animate-pulse">
            <div className="h-4 bg-muted rounded w-3/4"></div>
            <div className="h-4 bg-muted rounded w-1/2"></div>
            <div className="h-8 bg-muted rounded"></div>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-4">
            Agent is working on this task...
          </p>
        </CardContent>
      )}

      {/* Failed State - Show error */}
      {toolCall.status === "failed" && toolCall.error && (
        <CardContent className="pt-0">
          <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3">
            <p className="text-xs text-destructive font-medium">Error:</p>
            <p className="text-xs text-destructive/80 mt-1">{toolCall.error}</p>
          </div>
        </CardContent>
      )}

      {/* Completed State - Show full result details */}
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
          {toolCall.type === "progress_tracking" && (
            <ProgressTrackingResult result={toolCall.result} />
          )}
          {toolCall.type === "context_update" && (
            <ContextUpdateResult result={toolCall.result} />
          )}
        </CardContent>
      )}

      {/* Fallback: Show result even if status is not completed but result exists */}
      {toolCall.status !== "completed" && toolCall.status !== "failed" && toolCall.result && (
        <CardContent className="pt-0">
          <div className="text-xs text-muted-foreground bg-muted/30 p-2 rounded">
            <div className="font-medium mb-1">Partial result available:</div>
            <pre className="text-[10px] overflow-auto max-h-32">
              {JSON.stringify(toolCall.result, null, 2)}
            </pre>
          </div>
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
const SchedulerResult = ({ result }: { result: any }) => {
  console.log("SchedulerResult - Raw result:", result);
  console.log("SchedulerResult - Result type:", typeof result);
  
  // Parse JSON string if needed
  let parsedResult = result;
  if (typeof result === 'string') {
    try {
      parsedResult = JSON.parse(result);
      console.log("SchedulerResult - Parsed result:", parsedResult);
    } catch (e) {
      console.error("Failed to parse scheduler result:", e);
      return (
        <div className="text-xs space-y-2">
          <div className="text-muted-foreground">Raw result:</div>
          <div className="bg-muted/50 p-2 rounded font-mono text-[10px] break-all">{result}</div>
        </div>
      );
    }
  }

  // The result structure from workflow_tools.py:
  // {
  //   "status": "success",
  //   "meeting_name": "...",
  //   "event_id": "...",
  //   "calendar_link": "...",
  //   "meeting_link": "...",
  //   "scheduled_time": "...",
  //   "duration_minutes": 30,
  //   "attendees": ["email@example.com"],
  //   "location": "...",
  //   "description": "...",
  //   "reasoning": "..."
  // }
  
  const status = parsedResult.status;
  const title = parsedResult.meeting_name || parsedResult.title || "Event Scheduled";
  const startTime = parsedResult.scheduled_time || parsedResult.start_time;
  const duration = parsedResult.duration_minutes;
  const attendees = parsedResult.attendees || [];
  const location = parsedResult.location;
  const meetingLink = parsedResult.meeting_link;
  const calendarLink = parsedResult.calendar_link;
  const eventId = parsedResult.event_id;
  const description = parsedResult.description;
  const reasoning = parsedResult.reasoning;

  console.log("SchedulerResult - Extracted data:", {
    status, title, startTime, duration, attendees, location, meetingLink, calendarLink, eventId
  });

  // If scheduling failed
  if (status === "failed") {
    return (
      <div className="text-xs space-y-2">
        <div className="text-destructive bg-destructive/10 p-2 rounded">
          ❌ Scheduling failed
        </div>
        {(parsedResult.reason || reasoning) && (
          <div className="text-muted-foreground">{parsedResult.reason || reasoning}</div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Event Title and Time */}
      <div className="flex items-start gap-2">
        <Calendar className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
        <div className="flex-1 space-y-1">
          <p className="text-sm font-semibold text-foreground">{title}</p>
          {startTime && (
            <>
              <p className="text-xs text-muted-foreground">
                📅 {new Date(startTime).toLocaleDateString(undefined, { 
                  weekday: 'short', 
                  month: 'short', 
                  day: 'numeric',
                  year: 'numeric'
                })}
              </p>
              <p className="text-xs text-muted-foreground">
                ⏰ {new Date(startTime).toLocaleTimeString(undefined, { 
                  hour: 'numeric', 
                  minute: '2-digit' 
                })}
                {duration && ` (${duration} min)`}
              </p>
            </>
          )}
        </div>
      </div>

      {/* Description */}
      {description && (
        <div className="text-xs bg-muted/30 px-2 py-1.5 rounded">
          {description}
        </div>
      )}

      {/* Location */}
      {location && (
        <div className="text-xs bg-muted/50 px-2 py-1.5 rounded">
          📍 {location}
        </div>
      )}

      {/* Attendees */}
      {attendees && attendees.length > 0 && (
        <div className="text-xs bg-muted/50 px-2 py-1.5 rounded">
          <span className="font-medium">👥 Attendees:</span>
          <div className="mt-1 space-y-0.5">
            {attendees.map((email: string, idx: number) => (
              <div key={idx} className="text-muted-foreground">• {email}</div>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="space-y-1.5">
        {meetingLink && (
          <Button
            variant="default"
            size="sm"
            className="w-full text-xs"
            onClick={() => {
              window.open(meetingLink, "_blank");
            }}
          >
            Join Google Meet
          </Button>
        )}
        {calendarLink && (
          <Button
            variant="outline"
            size="sm"
            className="w-full text-xs"
            onClick={() => {
              window.open(calendarLink, "_blank");
            }}
          >
            View in Calendar
          </Button>
        )}
        {eventId && (
          <Button
            variant="destructive"
            size="sm"
            className="w-full text-xs"
            onClick={() => {
              // TODO: Implement cancel meeting functionality
              console.log("Cancel meeting:", eventId);
              alert("Cancel meeting functionality coming soon!");
            }}
          >
            Cancel Meeting
          </Button>
        )}
      </div>

      {/* Event ID for reference */}
      {eventId && (
        <p className="text-[10px] text-muted-foreground/60 text-center break-all">
          Event ID: {eventId}
        </p>
      )}
    </div>
  );
};

// Result component for assessment
const AssessmentResult = ({ result }: { result: any }) => {
  // Extract assessment details from various possible structures
  const assessment = result.assessment || result;
  const effortHours = assessment.effort_hours_most || assessment.effort_estimates?.effort_hours_most || assessment.effort_estimates?.most_likely_hours;
  const difficulty = assessment.difficulty_1to5;
  const riskScore = assessment.risk_score_0to100;
  const confidence = assessment.confidence_0to1;
  const milestones = assessment.milestones || [];
  const deliverables = assessment.deliverables || [];

  return (
    <div className="space-y-3">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-2">
        {effortHours !== undefined && (
          <div className="bg-blue-50 dark:bg-blue-950/30 px-2 py-1.5 rounded text-center">
            <div className="text-[10px] text-muted-foreground">Effort</div>
            <div className="text-sm font-semibold text-blue-700 dark:text-blue-400">
              {effortHours.toFixed(1)}h
            </div>
          </div>
        )}
        {difficulty !== undefined && (
          <div className="bg-orange-50 dark:bg-orange-950/30 px-2 py-1.5 rounded text-center">
            <div className="text-[10px] text-muted-foreground">Difficulty</div>
            <div className="text-sm font-semibold text-orange-700 dark:text-orange-400">
              {difficulty.toFixed(1)}/5
            </div>
          </div>
        )}
      </div>

      {/* Risk Score */}
      {riskScore !== undefined && (
        <div className="flex items-center justify-between text-xs bg-muted/50 px-2 py-1.5 rounded">
          <span className="text-muted-foreground">Risk Score:</span>
          <Badge 
            variant={riskScore > 70 ? "destructive" : riskScore > 40 ? "default" : "secondary"}
            className="text-xs"
          >
            {riskScore}/100
          </Badge>
        </div>
      )}

      {/* Confidence */}
      {confidence !== undefined && (
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Confidence:</span>
          <span className="font-medium">{(confidence * 100).toFixed(0)}%</span>
        </div>
      )}

      {/* Milestones */}
      {milestones.length > 0 && (
        <div>
          <p className="text-xs font-semibold mb-1.5">📋 Milestones:</p>
          <div className="space-y-1">
            {milestones.slice(0, 3).map((milestone: any, idx: number) => (
              <div key={idx} className="text-xs bg-muted/30 px-2 py-1 rounded">
                • {typeof milestone === "string" ? milestone : milestone.label || milestone.title || milestone.name}
              </div>
            ))}
            {milestones.length > 3 && (
              <p className="text-xs text-muted-foreground italic pl-2">
                +{milestones.length - 3} more milestones
              </p>
            )}
          </div>
        </div>
      )}

      {/* Deliverables */}
      {deliverables.length > 0 && (
        <div>
          <p className="text-xs font-semibold mb-1.5">📦 Deliverables:</p>
          <div className="space-y-1">
            {deliverables.slice(0, 2).map((item: any, idx: number) => (
              <div key={idx} className="text-xs text-muted-foreground px-2">
                • {typeof item === "string" ? item : item.name || item.title}
              </div>
            ))}
            {deliverables.length > 2 && (
              <p className="text-xs text-muted-foreground italic pl-2">
                +{deliverables.length - 2} more
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

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

// Result component for progress tracking
const ProgressTrackingResult = ({ result }: { result: any }) => {
  const minutes = result.minutes || result.duration_minutes;
  const assignmentTitle = result.assignment_title || result.assignment;
  const hoursLogged = minutes ? (minutes / 60).toFixed(1) : null;
  
  return (
    <div className="space-y-2">
      <div className="bg-green-50 dark:bg-green-950/30 px-3 py-2 rounded">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Study Time Logged</span>
          <span className="text-sm font-semibold text-green-700 dark:text-green-400">
            {hoursLogged ? `${hoursLogged}h` : `${minutes}m`}
          </span>
        </div>
      </div>
      
      {assignmentTitle && (
        <div className="text-xs bg-muted/50 px-2 py-1.5 rounded">
          <span className="font-medium">Assignment:</span> {assignmentTitle}
        </div>
      )}
      
      {result.hours_done !== undefined && (
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Total Hours Done:</span>
          <span className="font-medium">{result.hours_done.toFixed(1)}h</span>
        </div>
      )}
      
      {result.hours_remaining !== undefined && (
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Hours Remaining:</span>
          <span className="font-medium">{result.hours_remaining.toFixed(1)}h</span>
        </div>
      )}
    </div>
  );
};

// Result component for context update
const ContextUpdateResult = ({ result }: { result: any }) => {
  const coursesUpdated = result.courses_updated || result.courses || 0;
  const assignmentsUpdated = result.assignments_updated || result.assignments || 0;
  const documentsIngested = result.documents_ingested || result.documents || 0;
  
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-blue-50 dark:bg-blue-950/30 px-2 py-1.5 rounded text-center">
          <div className="text-[10px] text-muted-foreground">Courses</div>
          <div className="text-sm font-semibold text-blue-700 dark:text-blue-400">
            {coursesUpdated}
          </div>
        </div>
        <div className="bg-purple-50 dark:bg-purple-950/30 px-2 py-1.5 rounded text-center">
          <div className="text-[10px] text-muted-foreground">Assignments</div>
          <div className="text-sm font-semibold text-purple-700 dark:text-purple-400">
            {assignmentsUpdated}
          </div>
        </div>
        <div className="bg-green-50 dark:bg-green-950/30 px-2 py-1.5 rounded text-center">
          <div className="text-[10px] text-muted-foreground">Documents</div>
          <div className="text-sm font-semibold text-green-700 dark:text-green-400">
            {documentsIngested}
          </div>
        </div>
      </div>
      
      {result.status && (
        <div className="text-xs bg-muted/50 px-2 py-1.5 rounded text-center">
          {result.status}
        </div>
      )}
      
      {result.message && (
        <div className="text-xs text-muted-foreground">
          {result.message}
        </div>
      )}
    </div>
  );
};

