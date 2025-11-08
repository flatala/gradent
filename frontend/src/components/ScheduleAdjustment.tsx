import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Calendar,
  Clock,
  TrendingUp,
  ArrowRight,
  CheckCircle2,
  ArrowLeft,
} from "lucide-react";

interface ScheduleAdjustmentProps {
  results: any;
  onBack: () => void;
}

const ScheduleAdjustment = ({ results, onBack }: ScheduleAdjustmentProps) => {
  const handleSync = () => {
    // Simulate calendar sync
    setTimeout(() => {
      onBack();
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="max-w-5xl mx-auto py-8 space-y-6 animate-fade-in">
        {/* Back Button */}
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Button>

        {/* Header */}
        <div className="text-center space-y-2">
          <h2 className="text-3xl font-bold">Schedule Adjustment</h2>
          <p className="text-muted-foreground">
            We've optimized your study plan based on your mock exam results
          </p>
        </div>

        {/* Summary Card */}
        <Card className="p-6 bg-gradient-card shadow-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-primary/10 rounded-lg">
                <TrendingUp className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  Total Adjustment
                </p>
                <p className="text-2xl font-bold">+1h 20m to Linear Algebra</p>
              </div>
            </div>
            <Badge className="bg-success text-success-foreground">
              <CheckCircle2 className="mr-1 h-3 w-3" />
              Optimized
            </Badge>
          </div>
        </Card>

        {/* Changes Overview */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Added */}
          <Card className="p-6 bg-gradient-card">
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <div className="p-2 bg-success/10 rounded-lg">
                  <Calendar className="h-5 w-5 text-success" />
                </div>
                <h3 className="text-xl font-semibold">Added Study Blocks</h3>
              </div>

              <div className="space-y-3">
                <div className="p-4 bg-success-light rounded-lg border border-success/20">
                  <div className="flex items-start justify-between mb-2">
                    <p className="font-medium">{results.assignment.course}</p>
                    <Badge variant="outline" className="text-xs">
                      New
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    <span>Tuesday, 6:00 PM - 7:20 PM</span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    Focus: Eigenvalues & Vector Spaces
                  </p>
                </div>

                <div className="p-4 bg-success-light rounded-lg border border-success/20">
                  <div className="flex items-start justify-between mb-2">
                    <p className="font-medium">{results.assignment.course}</p>
                    <Badge variant="outline" className="text-xs">
                      New
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    <span>Thursday, 5:00 PM - 6:00 PM</span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    Practice problems & review
                  </p>
                </div>
              </div>
            </div>
          </Card>

          {/* Reduced */}
          <Card className="p-6 bg-gradient-card">
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <div className="p-2 bg-warning/10 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-warning" />
                </div>
                <h3 className="text-xl font-semibold">Adjusted Blocks</h3>
              </div>

              <div className="space-y-3">
                <div className="p-4 bg-muted rounded-lg border border-border">
                  <div className="flex items-start justify-between mb-2">
                    <p className="font-medium">PSYCH 101 Study</p>
                    <Badge variant="outline" className="text-xs">
                      Modified
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-muted-foreground line-through">
                      Sunday, 1:00 PM - 2:00 PM
                    </span>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">1:00 PM - 1:30 PM</span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    Reduced by 30 minutes
                  </p>
                </div>

                <div className="p-4 bg-muted rounded-lg border border-border">
                  <div className="flex items-start justify-between mb-2">
                    <p className="font-medium">CS 2402 Review</p>
                    <Badge variant="outline" className="text-xs">
                      Modified
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-muted-foreground line-through">
                      Saturday, 3:00 PM - 4:30 PM
                    </span>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">3:00 PM - 3:50 PM</span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    Reduced by 40 minutes
                  </p>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Sync Action */}
        <Card className="p-8 bg-gradient-primary text-white shadow-glow">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div>
              <h3 className="text-2xl font-semibold mb-2">Ready to Update?</h3>
              <p className="text-white/90">
                These changes will be synced to your Google Calendar
                automatically
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="secondary" onClick={onBack} size="lg">
                Review Later
              </Button>
              <Button
                onClick={handleSync}
                size="lg"
                className="bg-white text-primary hover:bg-white/90 shadow-md"
              >
                <CheckCircle2 className="mr-2 h-5 w-5" />
                Sync to Calendar
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default ScheduleAdjustment;
