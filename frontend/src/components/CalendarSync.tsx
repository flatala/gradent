import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Calendar, CheckCircle2, Clock, RefreshCw } from "lucide-react";

type CalendarEvent = {
  id: string;
  title: string;
  start: string;
  end: string;
  type: "study" | "exam" | "assignment";
};

export function CalendarSync() {
  const [isConnected, setIsConnected] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [lastSync, setLastSync] = useState<Date | null>(null);

  const mockEvents: CalendarEvent[] = [
    {
      id: "1",
      title: "Linear Algebra Study Block",
      start: "2025-11-12T18:00:00",
      end: "2025-11-12T19:20:00",
      type: "study",
    },
    {
      id: "2",
      title: "Linear Algebra Study Block",
      start: "2025-11-14T17:00:00",
      end: "2025-11-14T18:00:00",
      type: "study",
    },
    {
      id: "3",
      title: "Linear Algebra Midterm",
      start: "2025-11-15T14:00:00",
      end: "2025-11-15T16:00:00",
      type: "exam",
    },
    {
      id: "4",
      title: "Psychology Essay Due",
      start: "2025-11-18T23:59:00",
      end: "2025-11-18T23:59:00",
      type: "assignment",
    },
  ];

  const handleConnect = () => {
    setIsSyncing(true);
    setTimeout(() => {
      setIsConnected(true);
      setEvents(mockEvents);
      setLastSync(new Date());
      setIsSyncing(false);
    }, 2000);
  };

  const handleSync = () => {
    setIsSyncing(true);
    setTimeout(() => {
      setLastSync(new Date());
      setIsSyncing(false);
    }, 1500);
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  };

  const getEventTypeColor = (type: string) => {
    switch (type) {
      case "study":
        return "bg-primary/10 text-primary border-primary/20";
      case "exam":
        return "bg-destructive/10 text-destructive border-destructive/20";
      case "assignment":
        return "bg-warning/10 text-warning border-warning/20";
      default:
        return "bg-muted text-muted-foreground";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Google Calendar Sync</h2>
          <p className="text-muted-foreground text-sm">
            Manage your study schedule automatically
          </p>
        </div>
        {isConnected ? (
          <div className="flex items-center gap-3">
            <Button
              onClick={handleSync}
              variant="outline"
              disabled={isSyncing}
              className="gap-2"
            >
              <RefreshCw
                className={`h-4 w-4 ${isSyncing ? "animate-spin" : ""}`}
              />
              Sync Now
            </Button>
            {lastSync && (
              <Badge variant="outline" className="gap-1">
                <CheckCircle2 className="h-3 w-3" />
                Synced {Math.floor((Date.now() - lastSync.getTime()) / 60000)}m
                ago
              </Badge>
            )}
          </div>
        ) : (
          <Button
            onClick={handleConnect}
            disabled={isSyncing}
            className="gap-2"
          >
            <Calendar className="h-4 w-4" />
            Connect Google Calendar
          </Button>
        )}
      </div>

      {!isConnected ? (
        <Card className="p-8 text-center bg-gradient-card">
          <div className="max-w-md mx-auto">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <Calendar className="h-8 w-8 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">
              Connect Your Calendar
            </h3>
            <p className="text-muted-foreground mb-6">
              Sync your study blocks and exam schedules directly to Google
              Calendar. Study Autopilot will automatically manage your time
              based on performance.
            </p>
            <Button onClick={handleConnect} size="lg" disabled={isSyncing}>
              {isSyncing ? "Connecting..." : "Connect Google Calendar"}
            </Button>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          <Card className="p-6 bg-gradient-card">
            <h3 className="font-semibold mb-4">Upcoming Events</h3>
            <div className="space-y-3">
              {events.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-3 p-3 rounded-lg bg-background/50 border border-border/50"
                >
                  <div className="p-2 rounded bg-background">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm">{event.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(event.start)} • {formatTime(event.start)} -{" "}
                      {formatTime(event.end)}
                    </p>
                  </div>
                  <Badge
                    variant="outline"
                    className={`text-xs shrink-0 ${getEventTypeColor(event.type)}`}
                  >
                    {event.type}
                  </Badge>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6 bg-gradient-card">
            <h3 className="font-semibold mb-3">Sync Status</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Events</span>
                <span className="font-medium">{events.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Study Blocks</span>
                <span className="font-medium">
                  {events.filter((e) => e.type === "study").length}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Exams</span>
                <span className="font-medium">
                  {events.filter((e) => e.type === "exam").length}
                </span>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
