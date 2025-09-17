import { useQuery } from "@tanstack/react-query";
import { useBotStatus } from "@/hooks/use-bot-status";
import StatCard from "@/components/ui/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiRequest } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { UserPlus, Heart, Eye, Mail, Users, BarChart3, Clock } from "lucide-react";
import type { DailyStats, DailyLimits, ActivityLog } from "@shared/schema";

export default function Dashboard() {
  const { toast } = useToast();
  const { data: botStatus } = useBotStatus();
  
  const { data: dailyStats, refetch: refetchStats } = useQuery<DailyStats>({
    queryKey: ["/api/stats/daily"],
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: dailyLimits } = useQuery<DailyLimits>({
    queryKey: ["/api/limits"],
  });

  const { data: activityLogs } = useQuery<ActivityLog[]>({
    queryKey: ["/api/activity-logs"],
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  const handleQuickAction = async (action: string) => {
    try {
      let endpoint = "";
      let message = "";
      
      switch (action) {
        case "likeFollowers":
          endpoint = "/api/actions/like-followers";
          message = "Started liking followers' posts";
          break;
        case "viewStories":
          endpoint = "/api/actions/view-stories";
          message = "Started viewing stories";
          break;
        default:
          return;
      }
      
      await apiRequest("POST", endpoint);
      toast({
        title: "Action Started",
        description: message,
      });
      
      // Refresh stats after a delay
      setTimeout(() => {
        refetchStats();
      }, 3000);
      
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to start action",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="p-6 space-y-6" data-testid="dashboard-content">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-muted-foreground">Monitor and control your Instagram automation bot</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Today's Follows"
          value={dailyStats?.follows || 0}
          limit={dailyLimits?.follows_limit || 50}
          icon={UserPlus}
          color="blue"
          data-testid="stat-follows"
        />
        <StatCard
          title="Today's Unfollows"
          value={dailyStats?.unfollows || 0}
          limit={dailyLimits?.unfollows_limit || 50}
          icon={Users}
          color="red"
          data-testid="stat-unfollows"
        />
        <StatCard
          title="Today's Likes"
          value={dailyStats?.likes || 0}
          limit={dailyLimits?.likes_limit || 200}
          icon={Heart}
          color="purple"
          data-testid="stat-likes"
        />
        <StatCard
          title="Story Views"
          value={dailyStats?.story_views || 0}
          limit={dailyLimits?.story_views_limit || 500}
          icon={Eye}
          color="green"
          data-testid="stat-story-views"
        />
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Button
              onClick={() => handleQuickAction("likeFollowers")}
              className="p-4 h-auto flex flex-col items-center space-y-2"
              data-testid="button-like-followers"
            >
              <Heart className="h-5 w-5" />
              <span className="text-sm font-medium">Like Posts</span>
            </Button>
            <Button
              variant="secondary"
              onClick={() => handleQuickAction("viewStories")}
              className="p-4 h-auto flex flex-col items-center space-y-2"
              data-testid="button-view-stories"
            >
              <Eye className="h-5 w-5" />
              <span className="text-sm font-medium">View Stories</span>
            </Button>
            <Button
              variant="outline"
              className="p-4 h-auto flex flex-col items-center space-y-2"
              data-testid="button-follow-users"
            >
              <UserPlus className="h-5 w-5" />
              <span className="text-sm font-medium">Follow Users</span>
            </Button>
            <Button
              variant="outline"
              className="p-4 h-auto flex flex-col items-center space-y-2"
              data-testid="button-send-dms"
            >
              <Mail className="h-5 w-5" />
              <span className="text-sm font-medium">Send DMs</span>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity & System Health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4" data-testid="recent-activity">
              {activityLogs?.slice(0, 5).map((log, index) => (
                <div key={log.id} className="flex items-center space-x-3 p-3 bg-muted rounded-lg">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    log.status === 'success' ? 'bg-green-500' : 
                    log.status === 'error' ? 'bg-red-500' : 'bg-yellow-500'
                  }`}>
                    {log.action.includes('Follow') && <UserPlus className="h-4 w-4 text-white" />}
                    {log.action.includes('Like') && <Heart className="h-4 w-4 text-white" />}
                    {log.action.includes('View') && <Eye className="h-4 w-4 text-white" />}
                    {log.action.includes('DM') && <Mail className="h-4 w-4 text-white" />}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{log.details || log.action}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
              
              {(!activityLogs || activityLogs.length === 0) && (
                <div className="text-center text-muted-foreground py-8">
                  <BarChart3 className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No recent activity</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* System Health */}
        <Card>
          <CardHeader>
            <CardTitle>System Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4" data-testid="system-health">
              <div className="flex items-center justify-between">
                <span className="text-sm">Instagram Connection</span>
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    botStatus?.instagram_connected ? 'bg-green-500' : 'bg-red-500'
                  }`}></div>
                  <span className={`text-sm ${
                    botStatus?.instagram_connected ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {botStatus?.instagram_connected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Telegram Bot</span>
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    botStatus?.telegram_connected ? 'bg-green-500' : 'bg-red-500'
                  }`}></div>
                  <span className={`text-sm ${
                    botStatus?.telegram_connected ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {botStatus?.telegram_connected ? 'Online' : 'Offline'}
                  </span>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Bot Status</span>
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    botStatus?.bot_running ? 'bg-green-500' : 'bg-gray-500'
                  }`}></div>
                  <span className={`text-sm ${
                    botStatus?.bot_running ? 'text-green-600' : 'text-gray-600'
                  }`}>
                    {botStatus?.bot_running ? 'Running' : 'Stopped'}
                  </span>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Rate Limits</span>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                  <span className="text-sm text-yellow-600">
                    {Math.round(((dailyStats?.likes || 0) / (dailyLimits?.likes_limit || 200)) * 100)}% Used
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
