import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Bot, Clock, Webhook, Play, Calendar, Activity, Bell } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";

type ExecutionFrequency = "15min" | "30min" | "1hour" | "3hours" | "6hours" | "12hours" | "24hours";

interface AutonomousConfig {
  enabled: boolean;
  frequency: ExecutionFrequency;
  discord_webhook?: string;
  ntfy_topic?: string;
  last_execution?: string;
  next_execution?: string;
}

const FREQUENCY_OPTIONS = [
  { value: "15min", label: "Every 15 minutes" },
  { value: "30min", label: "Every 30 minutes" },
  { value: "1hour", label: "Every hour" },
  { value: "3hours", label: "Every 3 hours" },
  { value: "6hours", label: "Every 6 hours" },
  { value: "12hours", label: "Every 12 hours" },
  { value: "24hours", label: "Every 24 hours (Daily)" },
];

export default function AutonomousMode() {
  const [config, setConfig] = useState<AutonomousConfig>({
    enabled: false,
    frequency: "1hour",
    ntfy_topic: "gradent-ai-test-123",
  });
  const [discordWebhook, setDiscordWebhook] = useState("");
  const [ntfyTopic, setNtfyTopic] = useState("gradent-ai-test-123");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const { toast } = useToast();

  // Load current configuration
  useEffect(() => {
    const loadConfig = async () => {
      setLoading(true);
      try {
        const response = await api.getAutonomousConfig();
        setConfig(response);
        setDiscordWebhook(response.discord_webhook || "");
        setNtfyTopic(response.ntfy_topic || "gradent-ai-test-123");
      } catch (error) {
        console.error("Failed to load config:", error);
      } finally {
        setLoading(false);
      }
    };
    loadConfig();
  }, []);

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await api.updateAutonomousConfig({
        enabled: config.enabled,
        frequency: config.frequency,
        discord_webhook: discordWebhook || undefined,
        ntfy_topic: ntfyTopic || "gradent-ai-test-123",
      });
      toast({
        title: "Configuration saved",
        description: "Autonomous mode settings have been updated.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save configuration.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleToggleEnabled = async (enabled: boolean) => {
    setConfig({ ...config, enabled });
  };

  const handleTestWebhook = async () => {
    if (!discordWebhook) {
      toast({
        title: "Error",
        description: "Please enter a Discord webhook URL first.",
        variant: "destructive",
      });
      return;
    }
    
    setTesting(true);
    try {
      await api.testDiscordWebhook(discordWebhook);
      toast({
        title: "Success",
        description: "Test notification sent to Discord!",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send test notification. Check your webhook URL.",
        variant: "destructive",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleRunNow = async () => {
    setLoading(true);
    try {
      await api.triggerAutonomousExecution();
      toast({
        title: "Execution started",
        description: "Autonomous agent is now running...",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to trigger autonomous execution.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-3 bg-gradient-primary rounded-xl">
          <Bot className="h-6 w-6 text-white" />
        </div>
        <div>
          <h1 className="text-3xl font-bold">Autonomous Mode</h1>
          <p className="text-muted-foreground">
            Let the AI agent work for you automatically
          </p>
        </div>
      </div>

      {/* What the Agent Does */}
      <Card>
        <CardHeader>
          <CardTitle>What the Autonomous Agent Does</CardTitle>
          <CardDescription>
            The agent performs these tasks automatically
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-3">
            <li className="flex items-start gap-3">
              <div className="p-1.5 bg-primary/10 rounded-lg mt-0.5">
                <Calendar className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="font-medium text-sm">Schedule Management</p>
                <p className="text-xs text-muted-foreground">
                  Automatically schedules study sessions and review meetings
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <div className="p-1.5 bg-primary/10 rounded-lg mt-0.5">
                <Activity className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="font-medium text-sm">Assignment Assessment</p>
                <p className="text-xs text-muted-foreground">
                  Evaluates upcoming assignments and estimates effort required
                </p>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <div className="p-1.5 bg-primary/10 rounded-lg mt-0.5">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="font-medium text-sm">Study Suggestions</p>
                <p className="text-xs text-muted-foreground">
                  Generates personalized study recommendations based on your progress
                </p>
              </div>
            </li>
          </ul>
        </CardContent>
      </Card>

      {/* Status Card */}
      <Card className="border-2">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Agent Status
              </CardTitle>
              <CardDescription>
                {config.enabled ? "Active and running" : "Currently paused"}
              </CardDescription>
            </div>
            <Badge
              variant={config.enabled ? "default" : "secondary"}
              className="px-3 py-1"
            >
              {config.enabled ? "Active" : "Paused"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="enabled">Enable Autonomous Mode</Label>
              <p className="text-sm text-muted-foreground">
                Agent will run automatically based on schedule
              </p>
            </div>
            <Switch
              id="enabled"
              checked={config.enabled}
              onCheckedChange={handleToggleEnabled}
            />
          </div>

          {config.enabled && (
            <div className="pt-4 border-t space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Last Execution:
                </span>
                <span className="font-medium">
                  {config.last_execution
                    ? new Date(config.last_execution).toLocaleString()
                    : "Never"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Next Execution:
                </span>
                <span className="font-medium">
                  {config.next_execution
                    ? new Date(config.next_execution).toLocaleString()
                    : "Calculating..."}
                </span>
              </div>
            </div>
          )}

          <Button
            onClick={handleRunNow}
            className="w-full"
            disabled={loading}
          >
            <Play className="h-4 w-4 mr-2" />
            Run Now
          </Button>
        </CardContent>
      </Card>

      {/* Execution Frequency */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Execution Frequency
          </CardTitle>
          <CardDescription>
            How often should the autonomous agent run?
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="frequency">Frequency</Label>
            <Select
              value={config.frequency}
              onValueChange={(value: ExecutionFrequency) =>
                setConfig({ ...config, frequency: value })
              }
            >
              <SelectTrigger id="frequency">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FREQUENCY_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              The agent will automatically check for updates, assess assignments, generate
              suggestions, and schedule events based on this frequency.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Discord Webhook */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Webhook className="h-5 w-5" />
            Discord Notifications
          </CardTitle>
          <CardDescription>
            Receive notifications when the agent completes tasks
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="webhook">Discord Webhook URL</Label>
            <Input
              id="webhook"
              type="url"
              placeholder="https://discord.com/api/webhooks/..."
              value={discordWebhook}
              onChange={(e) => setDiscordWebhook(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Get your webhook URL from Discord Server Settings → Integrations → Webhooks
            </p>
          </div>
          <Button
            onClick={handleTestWebhook}
            variant="outline"
            className="w-full"
            disabled={testing || !discordWebhook}
          >
            {testing ? "Sending..." : "Send Test Notification"}
          </Button>
        </CardContent>
      </Card>

      {/* ntfy Notifications */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Mobile Notifications
          </CardTitle>
          <CardDescription>
            Get push notifications on mobile and desktop - no signup required!
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="ntfy-topic">Your Unique Topic Name</Label>
            <Input
              id="ntfy-topic"
              placeholder="my-study-ai-2024"
              value={ntfyTopic}
              onChange={(e) => setNtfyTopic(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              💡 Choose a unique name (e.g., your-name-gradent). 
              <strong> Mobile:</strong> Download ntfy app (iOS/Android). 
              <strong> Desktop:</strong> Visit ntfy.sh/your-topic-name
            </p>
          </div>
          
          {ntfyTopic && (
            <div className="bg-muted/50 p-4 rounded-lg space-y-3 text-sm">
              <p className="font-semibold text-foreground">📱 How to receive notifications:</p>
              <ul className="space-y-2">
                <li className="flex items-start gap-2">
                  <span className="text-primary font-bold">1.</span>
                  <div>
                    <strong>Mobile:</strong> Download ntfy app (iOS/Android), tap +, enter <code className="px-1 py-0.5 bg-background rounded text-xs">{ntfyTopic}</code>
                  </div>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary font-bold">2.</span>
                  <div>
                    <strong>Desktop:</strong> Visit{" "}
                    <a
                      href={`https://ntfy.sh/${ntfyTopic}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline font-mono text-xs"
                    >
                      ntfy.sh/{ntfyTopic}
                    </a>{" "}
                    and click Subscribe
                  </div>
                </li>
              </ul>
              <div className="pt-2 border-t border-border">
                <p className="text-xs text-muted-foreground">
                  🔒 <strong>Privacy tip:</strong> Use a unique, hard-to-guess topic name
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button
          onClick={handleSaveConfig}
          size="lg"
          disabled={saving}
          className="min-w-[200px]"
        >
          {saving ? "Saving..." : "Save Configuration"}
        </Button>
      </div>
    </div>
  );
}

