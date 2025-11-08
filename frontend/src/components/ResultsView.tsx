import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  XCircle,
  TrendingUp,
  Calendar,
  ArrowLeft,
} from "lucide-react";

interface ResultsViewProps {
  results: any;
  onViewSchedule: () => void;
  onBack: () => void;
}

const ResultsView = ({ results, onViewSchedule, onBack }: ResultsViewProps) => {
  const scoreColor: "success" | "warning" | "destructive" =
    results.score >= 80
      ? "success"
      : results.score >= 60
        ? "warning"
        : "destructive";

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="max-w-4xl mx-auto py-8 space-y-6 animate-fade-in">
        {/* Back Button */}
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>

        {/* Score Card */}
        <Card className="p-8 bg-gradient-card text-center shadow-lg">
          <div className="space-y-4">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-primary/10 rounded-full mb-4">
              <CheckCircle2 className="h-10 w-10 text-primary" />
            </div>
            <h2 className="text-3xl font-bold">Assessment Complete</h2>
            <p className="text-muted-foreground">{results.assignment.title}</p>

            <div className="py-8">
              <div className="inline-flex items-baseline gap-2">
                <span className="text-7xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                  {results.score}
                </span>
                <span className="text-3xl text-muted-foreground">/ 100</span>
              </div>
              <p className="text-lg text-muted-foreground mt-2">
                {results.correctAnswers} of {results.totalQuestions} correct
              </p>
            </div>

            <Badge variant={scoreColor} className="text-lg px-6 py-2">
              {results.score >= 80
                ? "Excellent"
                : results.score >= 60
                  ? "Good Progress"
                  : "Needs Work"}
            </Badge>
          </div>
        </Card>

        {/* Insights Grid */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Weak Topics */}
          <Card className="p-6 bg-gradient-card">
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-warning/10 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-warning" />
                </div>
                <h3 className="text-xl font-semibold">Areas to Focus</h3>
              </div>

              <div className="space-y-3">
                {results.weakTopics.map((topic: string, index: number) => (
                  <div
                    key={index}
                    className="p-4 bg-muted rounded-lg border border-border"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-medium mb-1">{topic}</p>
                        <p className="text-sm text-muted-foreground">
                          Review recommended materials
                        </p>
                      </div>
                      <XCircle className="h-5 w-5 text-warning shrink-0" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          {/* Recommendations */}
          <Card className="p-6 bg-gradient-card">
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-accent/10 rounded-lg">
                  <Calendar className="h-5 w-5 text-accent" />
                </div>
                <h3 className="text-xl font-semibold">Next Steps</h3>
              </div>

              <div className="space-y-3">
                <div className="p-4 bg-success-light rounded-lg border border-success/20">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-success shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium mb-1">Increased study time</p>
                      <p className="text-sm text-muted-foreground">
                        +1h 20m allocated to weak topics
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-success-light rounded-lg border border-success/20">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-success shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium mb-1">Practice materials</p>
                      <p className="text-sm text-muted-foreground">
                        3 recommended exercises added
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-success-light rounded-lg border border-success/20">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-success shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium mb-1">Schedule optimized</p>
                      <p className="text-sm text-muted-foreground">
                        Study blocks rebalanced this week
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Action */}
        <Card className="p-6 bg-gradient-primary text-white shadow-glow">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold mb-1">Schedule Updated</h3>
              <p className="text-white/90">
                Your calendar has been optimized based on these results
              </p>
            </div>
            <Button
              onClick={onViewSchedule}
              size="lg"
              variant="secondary"
              className="shadow-md"
            >
              View Changes
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default ResultsView;
