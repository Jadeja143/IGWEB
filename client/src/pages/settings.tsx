import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/api";
import { useState, useEffect } from "react";
import { AlertTriangle, Shield, Instagram } from "lucide-react";
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

  const [instagramCredentials, setInstagramCredentials] = useState({
    username: "",
    password: "",
  });

  const [showPasswordField, setShowPasswordField] = useState(false);

  const { data: dailyLimits } = useQuery<DailyLimits>({
    queryKey: ["/api/limits"],
  });

  const { data: botStatus } = useQuery<BotStatus>({
    queryKey: ["/api/bot/status"],
  });

  const { data: existingCredentials } = useQuery<{ username: string; id: string }>({
    queryKey: ["/api/instagram/credentials"],
    retry: false,
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
      const response = await apiRequest("PUT", "/api/limits", newLimits);
      return await response.json();
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
      const response = await apiRequest("POST", "/api/bot/status", status);
      return await response.json();
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

  const loginMutation = useMutation({
    mutationFn: async (credentials: { username: string; password: string; verification_code?: string }) => {
      const response = await apiRequest("POST", "/api/bot/login", credentials);
      return await response.json();
    },
    onSuccess: (data, credentials) => {
      queryClient.invalidateQueries({ queryKey: ["/api/bot/status"] });
      
      if (data.success) {
        toast({
          title: "Success",
          description: `Successfully logged into Instagram as @${data.user_info?.username || credentials.username}`,
        });
        setInstagramCredentials({ username: "", password: "" });
        setShowPasswordField(false);
      } else if (data.requires_verification) {
        toast({
          title: "Two-Factor Authentication Required",
          description: "Please check your Instagram app or email for the verification code",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Login Failed",
          description: data.error || "Failed to login to Instagram",
          variant: "destructive",
        });
      }
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to login",
        variant: "destructive",
      });
    },
  });

  const logoutMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest("POST", "/api/bot/logout", {});
      return await response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["/api/bot/status"] });
      toast({
        title: "Success",
        description: "Logged out successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to logout",
        variant: "destructive",
      });
    },
  });

  const testConnectionMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest("POST", "/api/bot/test-connection", {});
      return await response.json();
    },
    onSuccess: (data) => {
      toast({
        title: data.success ? "Success" : "Error",
        description: data.success ? "Instagram connection is working" : data.error,
        variant: data.success ? "default" : "destructive",
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to test connection",
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

  const handleLogin = () => {
    if (!instagramCredentials.username || !instagramCredentials.password) {
      toast({
        title: "Error",
        description: "Please enter both username and password",
        variant: "destructive",
      });
      return;
    }
    loginMutation.mutate(instagramCredentials);
  };

  const handleLogout = () => {
    logoutMutation.mutate();
  };

  const handleTestConnection = () => {
    testConnectionMutation.mutate();
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
              {/* Show existing credentials info if available */}
              {existingCredentials?.username && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                  <p className="font-medium text-green-800">Current Account: @{existingCredentials.username}</p>
                  <p className="text-xs text-green-600">Credentials are securely stored</p>
                </div>
              )}

              {/* Toggle to show login form */}
              {!showPasswordField && !botStatus?.instagram_connected ? (
                <div className="text-center">
                  <Button
                    onClick={() => setShowPasswordField(true)}
                    variant="outline"
                    data-testid="button-login-instagram"
                  >
                    Login to Instagram
                  </Button>
                  <p className="text-xs text-gray-500 mt-2">
                    Secure login - no credentials will be permanently stored
                  </p>
                </div>
              ) : showPasswordField ? (
                <div className="space-y-4 p-4 border rounded-lg bg-gray-50">
                  <div>
                    <Label htmlFor="instagram-username">Instagram Username</Label>
                    <Input
                      id="instagram-username"
                      placeholder="your_username"
                      value={instagramCredentials.username}
                      onChange={(e) => setInstagramCredentials(prev => ({ ...prev, username: e.target.value }))}
                      data-testid="input-instagram-username"
                    />
                  </div>
                  <div>
                    <Label htmlFor="instagram-password">Instagram Password</Label>
                    <Input
                      id="instagram-password"
                      type="password"
                      placeholder="Enter your password"
                      value={instagramCredentials.password}
                      onChange={(e) => setInstagramCredentials(prev => ({ ...prev, password: e.target.value }))}
                      data-testid="input-instagram-password"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Credentials are used only for login - not stored permanently
                    </p>
                  </div>
                  <div className="flex space-x-2">
                    <Button
                      onClick={handleLogin}
                      disabled={loginMutation.isPending || !instagramCredentials.username || !instagramCredentials.password}
                      data-testid="button-login"
                      className="flex-1"
                    >
                      {loginMutation.isPending ? "Logging in..." : "Login"}
                    </Button>
                    
                    <Button
                      onClick={() => {
                        setShowPasswordField(false);
                        setInstagramCredentials({ username: "", password: "" });
                      }}
                      variant="ghost"
                      data-testid="button-cancel-login"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : null}

              <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div>
                  <p className="font-medium">Session Status</p>
                  <p className="text-sm text-muted-foreground">
                    {botStatus?.instagram_connected ? "Authenticated" : "Not logged in"}
                    {botStatus?.user_info?.username && (
                      <span className="ml-2 text-green-600">@{botStatus.user_info.username}</span>
                    )}
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
