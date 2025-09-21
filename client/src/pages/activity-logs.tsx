import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { 
  Search, 
  Filter, 
  Download, 
  Calendar,
  UserPlus,
  Heart,
  Eye,
  Mail,
  Users,
  Clock,
  RefreshCw
} from "lucide-react";
import type { ActivityLog } from "@shared/schema";

export default function ActivityLogs() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [actionFilter, setActionFilter] = useState<string>("all");

  const { data: activityLogs, refetch, isLoading } = useQuery<ActivityLog[]>({
    queryKey: ["/api/activity-logs"],
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Filter logs based on search and filter criteria
  const filteredLogs = activityLogs?.filter(log => {
    const matchesSearch = log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (log.details && log.details.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesStatus = statusFilter === "all" || log.status === statusFilter;
    const matchesAction = actionFilter === "all" || log.action.toLowerCase().includes(actionFilter.toLowerCase());
    
    return matchesSearch && matchesStatus && matchesAction;
  }) || [];

  // Get unique actions for filter dropdown
  const uniqueActions = Array.from(new Set(activityLogs?.map(log => {
    const actionType = log.action.split(' ')[0]; // Get first word
    return actionType;
  }) || []));

  const getActionIcon = (action: string) => {
    if (action.toLowerCase().includes('follow')) return UserPlus;
    if (action.toLowerCase().includes('like')) return Heart;
    if (action.toLowerCase().includes('view') || action.toLowerCase().includes('story')) return Eye;
    if (action.toLowerCase().includes('dm') || action.toLowerCase().includes('message')) return Mail;
    if (action.toLowerCase().includes('unfollow')) return Users;
    return Clock;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'bg-green-500';
      case 'error': return 'bg-red-500';
      case 'warning': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusBadgeVariant = (status: string): "default" | "destructive" | "secondary" => {
    switch (status) {
      case 'success': return 'default';
      case 'error': return 'destructive';
      default: return 'secondary';
    }
  };

  const exportLogs = () => {
    if (!filteredLogs.length) return;
    
    const csvContent = [
      'Timestamp,Action,Status,Details',
      ...filteredLogs.map(log => 
        `${new Date(log.timestamp).toISOString()},${log.action},${log.status},"${log.details || ''}"`
      )
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `activity-logs-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  // Calculate statistics
  const stats = {
    total: activityLogs?.length || 0,
    success: activityLogs?.filter(log => log.status === 'success').length || 0,
    errors: activityLogs?.filter(log => log.status === 'error').length || 0,
    today: activityLogs?.filter(log => 
      new Date(log.timestamp || Date.now()).toDateString() === new Date().toDateString()
    ).length || 0,
  };

  return (
    <div className="p-6 space-y-6" data-testid="activity-logs-content">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Activity Logs</h1>
        <p className="text-muted-foreground">Monitor all automation activities and system events in real-time</p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Activities</CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">All time</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Successful</CardTitle>
            <div className="w-2 h-2 bg-green-500 rounded-full" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.success}</div>
            <p className="text-xs text-muted-foreground">
              {stats.total > 0 ? Math.round((stats.success / stats.total) * 100) : 0}% success rate
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Errors</CardTitle>
            <div className="w-2 h-2 bg-red-500 rounded-full" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.errors}</div>
            <p className="text-xs text-muted-foreground">
              {stats.total > 0 ? Math.round((stats.errors / stats.total) * 100) : 0}% error rate
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Today's Activities</CardTitle>
            <Calendar className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.today}</div>
            <p className="text-xs text-muted-foreground">
              Since midnight
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search logs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="p-2 border border-border rounded-md bg-background min-w-[120px]"
            >
              <option value="all">All Statuses</option>
              <option value="success">Success</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
            </select>

            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="p-2 border border-border rounded-md bg-background min-w-[120px]"
            >
              <option value="all">All Actions</option>
              {uniqueActions.map(action => (
                <option key={action} value={action}>{action}</option>
              ))}
            </select>

            <Button
              variant="outline"
              onClick={() => refetch()}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>

            <Button
              variant="outline"
              onClick={exportLogs}
              disabled={filteredLogs.length === 0}
            >
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Activity Logs Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Recent Activities</CardTitle>
            <Badge variant="secondary">
              {filteredLogs.length} of {activityLogs?.length || 0} logs
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left p-3">Time</th>
                  <th className="text-left p-3">Action</th>
                  <th className="text-left p-3">Status</th>
                  <th className="text-left p-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredLogs.map((log) => {
                  const Icon = getActionIcon(log.action);
                  return (
                    <tr key={log.id} className="hover:bg-muted/50">
                      <td className="p-3">
                        <div className="text-sm">
                          {new Date(log.timestamp || Date.now()).toLocaleString()}
                        </div>
                      </td>
                      <td className="p-3">
                        <div className="flex items-center space-x-2">
                          <div className={`w-6 h-6 rounded-full flex items-center justify-center ${getStatusColor(log.status)}`}>
                            <Icon className="h-3 w-3 text-white" />
                          </div>
                          <span className="font-medium">{log.action}</span>
                        </div>
                      </td>
                      <td className="p-3">
                        <Badge variant={getStatusBadgeVariant(log.status)}>
                          {log.status}
                        </Badge>
                      </td>
                      <td className="p-3">
                        <div className="text-sm text-muted-foreground max-w-md">
                          {log.details || 'No additional details'}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {filteredLogs.length === 0 && (
            <div className="text-center text-muted-foreground py-8">
              <Clock className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No activity logs found</p>
              {searchTerm || statusFilter !== "all" || actionFilter !== "all" ? (
                <p className="text-sm">Try adjusting your filters</p>
              ) : (
                <p className="text-sm">Start some automation tasks to see logs here</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}