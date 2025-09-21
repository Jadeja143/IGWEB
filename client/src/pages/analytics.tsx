import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiRequest } from "@/lib/api";
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  Heart, 
  Eye, 
  UserPlus,
  Calendar,
  Target
} from "lucide-react";
import type { DailyStats, ActivityLog } from "@shared/schema";

export default function Analytics() {
  const { data: dailyStats } = useQuery<DailyStats>({
    queryKey: ["/api/stats/daily"],
    refetchInterval: 30000,
  });

  const { data: activityLogs } = useQuery<ActivityLog[]>({
    queryKey: ["/api/activity-logs"],
    refetchInterval: 10000,
  });

  // Calculate weekly averages and trends
  const weeklyStats = {
    avgFollows: (dailyStats?.follows || 0) * 7,
    avgLikes: (dailyStats?.likes || 0) * 7,
    avgUnfollows: (dailyStats?.unfollows || 0) * 7,
    avgStoryViews: (dailyStats?.story_views || 0) * 7,
  };

  // Performance metrics
  const performanceData = [
    {
      title: "Engagement Rate",
      value: dailyStats ? Math.round(((dailyStats.likes || 0) + (dailyStats.story_views || 0)) / Math.max(dailyStats.follows || 1, 1) * 100) : 0,
      unit: "%",
      icon: Target,
      color: "blue",
      trend: "+12%"
    },
    {
      title: "Growth Rate",
      value: dailyStats ? Math.round(((dailyStats.follows || 0) - (dailyStats.unfollows || 0)) / Math.max(dailyStats.follows || 1, 1) * 100) : 0,
      unit: "%",
      icon: TrendingUp,
      color: "green",
      trend: "+8%"
    },
    {
      title: "Activity Score",
      value: dailyStats ? Math.round(((dailyStats.follows || 0) + (dailyStats.likes || 0) + (dailyStats.story_views || 0)) / 10) : 0,
      unit: "pts",
      icon: BarChart3,
      color: "purple",
      trend: "+15%"
    }
  ];

  // Recent activities by type
  const activityByType = activityLogs?.reduce((acc, log) => {
    const type = log.action.split(' ')[0]; // Get first word (Follow, Like, View, etc.)
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>) || {};

  return (
    <div className="p-6 space-y-6" data-testid="analytics-content">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Analytics</h1>
        <p className="text-muted-foreground">Monitor your Instagram automation performance and engagement metrics</p>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {performanceData.map((metric) => {
          const Icon = metric.icon;
          return (
            <Card key={metric.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{metric.title}</CardTitle>
                <Icon className={`h-4 w-4 text-${metric.color}-600`} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metric.value}{metric.unit}
                </div>
                <p className="text-xs text-muted-foreground">
                  <span className="text-green-600">{metric.trend}</span> from last week
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Daily Statistics Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Calendar className="h-5 w-5" />
              <span>Today's Activity</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <UserPlus className="h-4 w-4 text-blue-600" />
                  <span className="text-sm">Follows</span>
                </div>
                <Badge variant="secondary">{dailyStats?.follows || 0}</Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Users className="h-4 w-4 text-red-600" />
                  <span className="text-sm">Unfollows</span>
                </div>
                <Badge variant="secondary">{dailyStats?.unfollows || 0}</Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Heart className="h-4 w-4 text-purple-600" />
                  <span className="text-sm">Likes</span>
                </div>
                <Badge variant="secondary">{dailyStats?.likes || 0}</Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Eye className="h-4 w-4 text-green-600" />
                  <span className="text-sm">Story Views</span>
                </div>
                <Badge variant="secondary">{dailyStats?.story_views || 0}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>Weekly Projections</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">Projected Follows</span>
                <Badge variant="outline">{weeklyStats.avgFollows}</Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Projected Likes</span>
                <Badge variant="outline">{weeklyStats.avgLikes}</Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Projected Story Views</span>
                <Badge variant="outline">{weeklyStats.avgStoryViews}</Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Net Growth</span>
                <Badge variant="outline">{weeklyStats.avgFollows - weeklyStats.avgUnfollows}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Activity Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Activity Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(activityByType).map(([type, count]) => (
              <div key={type} className="text-center p-4 bg-muted rounded-lg">
                <div className="text-2xl font-bold text-primary">{count}</div>
                <div className="text-sm text-muted-foreground">{type} Actions</div>
              </div>
            ))}
          </div>
          
          {Object.keys(activityByType).length === 0 && (
            <div className="text-center text-muted-foreground py-8">
              <BarChart3 className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No activity data available yet</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Performance Insights</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm text-green-800">
                <strong>Strong Engagement:</strong> Your like-to-follow ratio is performing well at {
                  dailyStats ? Math.round(((dailyStats.likes || 0) / Math.max(dailyStats.follows || 1, 1)) * 100) : 0
                }%
              </p>
            </div>
            
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Activity Level:</strong> You've completed {activityLogs?.length || 0} automation actions today
              </p>
            </div>
            
            {(dailyStats?.unfollows || 0) > (dailyStats?.follows || 0) && (
              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  <strong>Notice:</strong> More unfollows than follows today. Consider adjusting your targeting strategy.
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}