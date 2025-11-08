import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Calendar, BookOpen, Shield } from "lucide-react";

interface ConsentModalProps {
  onConsent: () => void;
  onClose: () => void;
}

const ConsentModal = ({ onConsent, onClose }: ConsentModalProps) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm animate-fade-in">
      <Card className="max-w-md w-full mx-4 p-8 shadow-lg bg-gradient-card animate-slide-up">
        <div className="space-y-6">
          {/* Header */}
          <div className="text-center space-y-2">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <Shield className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-2xl font-bold">Connect Your Services</h2>
            <p className="text-muted-foreground">
              We'll read your assignments and create optimized study blocks in
              your calendar.
            </p>
          </div>

          {/* Services */}
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-3 bg-success-light rounded-lg border border-success/20">
              <div className="flex items-center justify-center w-10 h-10 bg-success/10 rounded-lg shrink-0">
                <BookOpen className="h-5 w-5 text-success" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">Brightspace</p>
                <p className="text-sm text-muted-foreground">
                  Read assignments & materials
                </p>
              </div>
              <CheckCircle2 className="h-5 w-5 text-success shrink-0" />
            </div>

            <div className="flex items-center gap-3 p-3 bg-success-light rounded-lg border border-success/20">
              <div className="flex items-center justify-center w-10 h-10 bg-success/10 rounded-lg shrink-0">
                <Calendar className="h-5 w-5 text-success" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">Google Calendar</p>
                <p className="text-sm text-muted-foreground">
                  Add study blocks & events
                </p>
              </div>
              <CheckCircle2 className="h-5 w-5 text-success shrink-0" />
            </div>
          </div>

          {/* Privacy Note */}
          <div className="p-4 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">
                Your privacy matters.
              </span>{" "}
              You can revoke access anytime from settings. We only read what's
              needed to help you study.
            </p>
          </div>

          {/* Actions */}
          <div className="space-y-2">
            <Button onClick={onConsent} className="w-full shadow-md" size="lg">
              Allow & Continue
            </Button>
            <Button onClick={onClose} variant="ghost" className="w-full">
              Not Now
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default ConsentModal;
