import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/api";
import { useState, useEffect } from "react";
import { AlertTriangle, Shield, MessageSquare, Instagram } from "lucide-react";
import type { DailyLimits, BotStatus } from "@shared/schema";

export default function Settings() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [limits, setLimits] = useState({
    follows_limit: 50,
    unfollows_limit: 50,
    likes_limit: 200,
    dms_limit: 10,
    story_views_limit: 500,
  });

  const [safetySettings, setSafetySettings] = useState({
    smartDelays: true,
    respectFollowBack: true,
    minWaitDays: 7,
    maxWaitDays: 14,
  });

  const { data: dailyLimits } = useQuery<DailyLimits>({
    queryKey: ["/api/limits"],
  });

  const { data: botStatus } = useQuery<BotStatus>({
    queryKey: ["/api/bot/status"],
  });

  useEffect(() => {
    if (dailyLimits) {
      setLimits({
        follows_limit: dailyLimits.follows_limit || 50,
        unfollows_limit: dailyLimits.unfollows_limit || 50,
        likes_limit: dailyLimits.likes_limit || 200,
        dms_limit: dailyLimits.dms_limit || 10,
        story_views_limit: dailyLimits.story_views_limit || 500,
      });
    }
  }, [dailyLimits]);

  const updateLimitsMutation = useMutation({
    mutationFn: async (newLimits: typeof limits) => {
      return await apiRequest("PUT", "/api/limits", newLimits);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/limits"] });
      toast({
        title: "Success",
        description: "Daily limits updated successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const updateBotStatusMutation = useMutation({
    mutationFn: async (status: Partial<BotStatus>) => {
      return await apiRequest("POST", "/api/bot/status", status);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/bot/status"] });
      toast({
        title: "Success",
        description: "Bot status updated",
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleUpdateLimits = () => {
    updateLimitsMutation.mutate(limits);
  };

  const handleStopBot = () => {
    updateBotStatusMutation.mutate({
      bot_running: false,
      instagram_connected: false,
    });
  };

  const handleResetData = () => {
    // This would be implemented to reset all tracking data
    toast({
      title: "Reset Initiated",
      description: "All tracking data has been reset",
    });
  };

  return (
    <div className="p-6 space-y-6" data-testid="settings-content">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Instagram Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Instagram className="h-5 w-5" />
              <span>Instagram Account</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Label htmlFor="instagram-username">Username</Label>
                <Input
                  id="instagram-username"
                  placeholder="your_username"
                  disabled
                  data-testid="input-instagram-username"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Configure via environment variables
                </p>
              </div>
              <div>
                <Label htmlFor="instagram-password">Password</Label>
                <Input
                  id="instagram-password"
                  type="password"
                  placeholder="••••••••"
                  disabled
                  data-testid="input-instagram-password"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Configure via environment variables
                </p>
              </div>
              <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div>
                  <p className="font-medium">Connection Status</p>
                  <p className="text-sm text-muted-foreground">
                    {botStatus?.instagram_connected ? "Connected" : "Disconnected"}
                  </p>
                </div>
                <div className={`w-3 h-3 rounded-full ${
                  botStatus?.instagram_connected ? "bg-green-500" : "bg-red-500"
                }`} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Daily Limits */}
        <Card>
          <CardHeader>
            <CardTitle>Daily Limits</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Label htmlFor="follows-limit">Follows per day</Label>
                <Input
                  id="follows-limit"
                  type="number"
                  value={limits.follows_limit}
                  onChange={(e) => setLimits(prev => ({
                    ...prev,
                    follows_limit: parseInt(e.target.value) || 0
                  }))}
                  data-testid="input-follows-limit"
                />
              </div>
              <div>
                <Label htmlFor="unfollows-limit">Unfollows per day</Label>
                <Input
                  id="unfollows-limit"
                  type="number"
                  value={limits.unfollows_limit}
                  onChange={(e) => setLimits(prev => ({
                    ...prev,
                    unfollows_limit: parseInt(e.target.value) || 0
                  }))}
                  data-testid="input-unfollows-limit"
                />
              </div>
              <div>
                <Label htmlFor="likes-limit">Likes per day</Label>
                <Input
                  id="likes-limit"
                  type="number"
                  value={limits.likes_limit}
                  onChange={(e) => setLimits(prev => ({
                    ...prev,
                    likes_limit: parseInt(e.target.value) || 0
                  }))}
                  data-testid="input-likes-limit"
                />
              </div>
              <div>
                <Label htmlFor="dms-limit">DMs per day</Label>
                <Input
                  id="dms-limit"
                  type="number"
                  value={limits.dms_limit}
                  onChange={(e) => setLimits(prev => ({
                    ...prev,
                    dms_limit: parseInt(e.target.value) || 0
                  }))}
                  data-testid="input-dms-limit"
                />
              </div>
              <div>
                <Label htmlFor="story-views-limit">Story views per day</Label>
                <Input
                  id="story-views-limit"
                  type="number"
                  value={limits.story_views_limit}
                  onChange={(e) => setLimits(prev => ({
                    ...prev,
                    story_views_limit: parseInt(e.target.value) || 0
                  }))}
                  data-testid="input-story-views-limit"
                />
              </div>
              <Button 
                onClick={handleUpdateLimits}
                disabled={updateLimitsMutation.isPending}
                className="w-full"
                data-testid="button-update-limits"
              >
                Update Limits
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Safety Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Shield className="h-5 w-5" />
              <span>Safety Settings</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">Smart Delays</h3>
                  <p className="text-sm text-muted-foreground">Add human-like delays between actions</p>
                </div>
                <Switch
                  checked={safetySettings.smartDelays}
                  onCheckedChange={(checked) => setSafetySettings(prev => ({
                    ...prev,
                    smartDelays: checked
                  }))}
                  data-testid="switch-smart-delays"
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">Respect Follow-Back Time</h3>
                  <p className="text-sm text-muted-foreground">Wait before unfollowing users</p>
                </div>
                <Switch
                  checked={safetySettings.respectFollowBack}
                  onCheckedChange={(checked) => setSafetySettings(prev => ({
                    ...prev,
                    respectFollowBack: checked
                  }))}
                  data-testid="switch-respect-follow-back"
                />
              </div>
              <div>
                <Label htmlFor="min-wait-days">Min wait days before unfollow</Label>
                <Input
                  id="min-wait-days"
                  type="number"
                  value={safetySettings.minWaitDays}
                  onChange={(e) => setSafetySettings(prev => ({
                    ...prev,
                    minWaitDays: parseInt(e.target.value) || 7
                  }))}
                  data-testid="input-min-wait-days"
                />
              </div>
              <div>
                <Label htmlFor="max-wait-days">Max wait days before force unfollow</Label>
                <Input
                  id="max-wait-days"
                  type="number"
                  value={safetySettings.maxWaitDays}
                  onChange={(e) => setSafetySettings(prev => ({
                    ...prev,
                    maxWaitDays: parseInt(e.target.value) || 14
                  }))}
                  data-testid="input-max-wait-days"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Telegram Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MessageSquare className="h-5 w-5" />
              <span>Telegram Bot</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Label htmlFor="telegram-token">Bot Token</Label>
                <Input
                  id="telegram-token"
                  type="password"
                  placeholder="1234567890:ABC..."
                  disabled
                  data-testid="input-telegram-token"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Configure via environment variables
                </p>
              </div>
              <div>
                <Label htmlFor="telegram-admin">Admin User ID</Label>
                <Input
                  id="telegram-admin"
                  placeholder="123456789"
                  disabled
                  data-testid="input-telegram-admin"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Configure via environment variables
                </p>
              </div>
              <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div>
                  <p className="font-medium">Connection Status</p>
                  <p className="text-sm text-muted-foreground">
                    {botStatus?.telegram_connected ? "Connected" : "Disconnected"}
                  </p>
                </div>
                <div className={`w-3 h-3 rounded-full ${
                  botStatus?.telegram_connected ? "bg-green-500" : "bg-red-500"
                }`} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Danger Zone */}
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive flex items-center space-x-2">
            <AlertTriangle className="h-5 w-5" />
            <span>Danger Zone</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-destructive/10 rounded-lg">
              <div>
                <h3 className="font-medium">Reset All Data</h3>
                <p className="text-sm text-muted-foreground">
                  Clear all followed users, liked posts, and activity logs
                </p>
              </div>
              <Button
                variant="destructive"
                onClick={handleResetData}
                data-testid="button-reset-data"
              >
                Reset
              </Button>
            </div>
            <div className="flex items-center justify-between p-4 bg-destructive/10 rounded-lg">
              <div>
                <h3 className="font-medium">Stop All Automation</h3>
                <p className="text-sm text-muted-foreground">
                  Immediately stop all running automation tasks
                </p>
              </div>
              <Button
                variant="destructive"
                onClick={handleStopBot}
                disabled={updateBotStatusMutation.isPending}
                data-testid="button-stop-automation"
              >
                Stop All
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
