import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/api";
import ProgressBar from "@/components/ui/progress-bar";
import { useState } from "react";
import { 
  UserPlus, 
  Heart, 
  Eye, 
  Mail,
  MapPin,
  Hash,
  Play,
  Pause
} from "lucide-react";
import type { DailyStats, DailyLimits } from "@shared/schema";

export default function Automation() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [hashtagInput, setHashtagInput] = useState("");
  const [locationInput, setLocationInput] = useState("");
  const [followAmount, setFollowAmount] = useState(20);

  const { data: dailyStats } = useQuery<DailyStats>({
    queryKey: ["/api/stats/daily"],
    refetchInterval: 30000,
  });

  const { data: dailyLimits } = useQuery<DailyLimits>({
    queryKey: ["/api/limits"],
  });

  const automationMutation = useMutation({
    mutationFn: async ({ action, data }: { action: string; data?: any }) => {
      return await apiRequest("POST", `/api/actions/${action}`, data);
    },
    onSuccess: (_, variables) => {
      toast({
        title: "Action Started",
        description: `${variables.action} task has been initiated`,
      });
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["/api/stats/daily"] });
      }, 3000);
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleFollowHashtag = () => {
    if (!hashtagInput.trim()) {
      toast({
        title: "Error",
        description: "Please enter a hashtag",
        variant: "destructive",
      });
      return;
    }
    
    automationMutation.mutate({
      action: "follow-hashtag",
      data: { hashtag: hashtagInput.replace("#", ""), amount: followAmount }
    });
    setHashtagInput("");
  };

  const handleFollowLocation = () => {
    if (!locationInput.trim()) {
      toast({
        title: "Error", 
        description: "Please enter a location",
        variant: "destructive",
      });
      return;
    }
    
    automationMutation.mutate({
      action: "follow-location",
      data: { location: locationInput, amount: followAmount }
    });
    setLocationInput("");
  };

  const modules = [
    {
      title: "Follow Module",
      icon: UserPlus,
      status: "Active",
      statusColor: "green",
      current: dailyStats?.follows || 0,
      limit: dailyLimits?.follows_limit || 50,
      actions: [
        { label: "Follow by Hashtag", action: "follow-hashtag", variant: "default" as const },
        { label: "Follow by Location", action: "follow-location", variant: "secondary" as const },
        { label: "Follow Followers", action: "follow-followers", variant: "outline" as const },
        { label: "Follow Suggested", action: "follow-suggested", variant: "outline" as const },
      ]
    },
    {
      title: "Like Module", 
      icon: Heart,
      status: "Active",
      statusColor: "green",
      current: dailyStats?.likes || 0,
      limit: dailyLimits?.likes_limit || 200,
      actions: [
        { label: "Like Followers", action: "like-followers", variant: "default" as const },
        { label: "Like Following", action: "like-following", variant: "secondary" as const },
        { label: "Like by Hashtag", action: "like-hashtag", variant: "outline" as const },
        { label: "Like by Location", action: "like-location", variant: "outline" as const },
      ]
    },
    {
      title: "Story Module",
      icon: Eye,
      status: "Active", 
      statusColor: "green",
      current: dailyStats?.story_views || 0,
      limit: dailyLimits?.story_views_limit || 500,
      actions: [
        { label: "View Followers", action: "view-followers-stories", variant: "default" as const },
        { label: "View Following", action: "view-following-stories", variant: "secondary" as const },
      ]
    },
    {
      title: "DM Module",
      icon: Mail,
      status: "Paused",
      statusColor: "yellow", 
      current: dailyStats?.dms || 0,
      limit: dailyLimits?.dms_limit || 10,
      actions: [
        { label: "Send Personalized DMs", action: "send-dms", variant: "default" as const },
        { label: "Configure Templates", action: "configure-templates", variant: "secondary" as const },
      ]
    }
  ];

  const scheduleData = [
    { task: "Follow by Hashtag", schedule: "Every 2 hours", lastRun: "2 min ago", status: "Active" },
    { task: "Like Followers", schedule: "Every 30 min", lastRun: "5 min ago", status: "Active" },
    { task: "Cleanup Unfollows", schedule: "Daily at 2 AM", lastRun: "6 hours ago", status: "Active" },
  ];

  return (
    <div className="p-6 space-y-6" data-testid="automation-content">
      {/* Module Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {modules.map((module) => {
          const Icon = module.icon;
          const percentage = module.limit > 0 ? (module.current / module.limit) * 100 : 0;
          
          return (
            <Card key={module.title}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center space-x-2">
                    <Icon className="h-5 w-5" />
                    <span>{module.title}</span>
                  </CardTitle>
                  <Badge variant={module.statusColor === "green" ? "default" : "secondary"}>
                    <div className={`w-2 h-2 rounded-full mr-2 ${
                      module.statusColor === "green" ? "bg-green-500" : "bg-yellow-500"
                    }`} />
                    {module.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-2">
                    {module.actions.map((action) => (
                      <Button
                        key={action.action}
                        variant={action.variant}
                        size="sm"
                        onClick={() => automationMutation.mutate({ action: action.action })}
                        disabled={automationMutation.isPending}
                        data-testid={`button-${action.action}`}
                      >
                        {action.label}
                      </Button>
                    ))}
                  </div>
                  <div className="p-3 bg-muted rounded-lg">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm">Daily Progress</span>
                      <span className="text-sm font-medium">{module.current}/{module.limit}</span>
                    </div>
                    <ProgressBar 
                      value={percentage} 
                      color={module.title.includes("Like") ? "purple" : 
                             module.title.includes("Follow") ? "blue" : 
                             module.title.includes("Story") ? "green" : "blue"}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Hash className="h-5 w-5" />
              <span>Follow by Hashtag</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Label htmlFor="hashtag-input">Hashtag (without #)</Label>
                <Input
                  id="hashtag-input"
                  value={hashtagInput}
                  onChange={(e) => setHashtagInput(e.target.value)}
                  placeholder="photography"
                  data-testid="input-hashtag"
                />
              </div>
              <div>
                <Label htmlFor="follow-amount">Number to follow</Label>
                <Input
                  id="follow-amount"
                  type="number"
                  value={followAmount}
                  onChange={(e) => setFollowAmount(parseInt(e.target.value) || 20)}
                  min="1"
                  max="100"
                  data-testid="input-follow-amount"
                />
              </div>
              <Button 
                onClick={handleFollowHashtag}
                disabled={automationMutation.isPending}
                className="w-full"
                data-testid="button-follow-hashtag-submit"
              >
                <Hash className="h-4 w-4 mr-2" />
                Follow Users from #{hashtagInput || "hashtag"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MapPin className="h-5 w-5" />
              <span>Follow by Location</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <Label htmlFor="location-input">Location Name</Label>
                <Input
                  id="location-input"
                  value={locationInput}
                  onChange={(e) => setLocationInput(e.target.value)}
                  placeholder="New York, NY"
                  data-testid="input-location"
                />
              </div>
              <div>
                <Label htmlFor="location-amount">Number to follow</Label>
                <Input
                  id="location-amount"
                  type="number"
                  value={followAmount}
                  onChange={(e) => setFollowAmount(parseInt(e.target.value) || 20)}
                  min="1"
                  max="100"
                  data-testid="input-location-amount"
                />
              </div>
              <Button 
                onClick={handleFollowLocation}
                disabled={automationMutation.isPending}
                className="w-full"
                data-testid="button-follow-location-submit"
              >
                <MapPin className="h-4 w-4 mr-2" />
                Follow Users from {locationInput || "location"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Automation Schedule */}
      <Card>
        <CardHeader>
          <CardTitle>Automation Schedule</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left p-3">Task</th>
                  <th className="text-left p-3">Schedule</th>
                  <th className="text-left p-3">Last Run</th>
                  <th className="text-left p-3">Status</th>
                  <th className="text-left p-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {scheduleData.map((item, index) => (
                  <tr key={index}>
                    <td className="p-3">{item.task}</td>
                    <td className="p-3">{item.schedule}</td>
                    <td className="p-3">{item.lastRun}</td>
                    <td className="p-3">
                      <Badge variant="default">
                        {item.status}
                      </Badge>
                    </td>
                    <td className="p-3">
                      <Button variant="link" size="sm" data-testid={`button-pause-${index}`}>
                        <Pause className="h-3 w-3 mr-1" />
                        Pause
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
