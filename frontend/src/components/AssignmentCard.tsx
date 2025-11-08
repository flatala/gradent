import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar, TrendingUp, Target } from "lucide-react";

interface Assignment {
  id: string;
  title: string;
  course: string;
  dueDate: string;
  weight: number;
  urgency: "high" | "medium" | "low";
  autoSelected: boolean;
  topics: string[];
}

interface AssignmentCardProps {
  assignment: Assignment;
  onStartExam: (assignment: Assignment) => void;
}

const AssignmentCard = ({ assignment, onStartExam }: AssignmentCardProps) => {
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

        {/* Topics */}
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">
            Key Topics
          </p>
          <div className="flex flex-wrap gap-2">
            {assignment.topics.map((topic, index) => (
              <Badge key={index} variant="secondary" className="text-xs">
                {topic}
              </Badge>
            ))}
          </div>
        </div>

        {/* Action */}
        <Button
          onClick={() => onStartExam(assignment)}
          className="w-full shadow-sm"
        >
          Start Mock Exam
        </Button>
      </div>
    </Card>
  );
};

export default AssignmentCard;
