import { Link, useLocation } from "wouter";
import { cn } from "@/lib/utils";
import { useBotStatus } from "@/hooks/use-bot-status";
import { 
  BarChart3, 
  Bot, 
  Users, 
  Hash, 
  Settings, 
  List,
  Instagram
} from "lucide-react";

const navItems = [
  { path: "/", label: "Dashboard", icon: BarChart3 },
  { path: "/automation", label: "Automation", icon: Bot },
  { path: "/users", label: "User Management", icon: Users },
  { path: "/content", label: "Content & Tags", icon: Hash },
  { path: "/analytics", label: "Analytics", icon: BarChart3 },
  { path: "/settings", label: "Settings", icon: Settings },
  { path: "/logs", label: "Activity Logs", icon: List },
];

export default function Sidebar() {
  const [location] = useLocation();
  const { data: botStatus } = useBotStatus();

  return (
    <aside className="w-64 bg-sidebar border-r border-sidebar-border flex flex-col" data-testid="sidebar">
      {/* Logo/Brand */}
      <div className="p-6 border-b border-sidebar-border">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-sidebar-primary rounded-lg flex items-center justify-center">
            <Instagram className="text-sidebar-primary-foreground text-lg" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-sidebar-foreground">InstaBotPro</h1>
            <p className="text-xs text-muted-foreground">Automation Dashboard</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => {
          const isActive = location === item.path;
          const Icon = item.icon;
          
          return (
            <Link key={item.path} href={item.path}>
              <a 
                className={cn(
                  "flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors",
                  isActive 
                    ? "sidebar-active" 
                    : "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground text-sidebar-foreground"
                )}
                data-testid={`nav-${item.path.replace('/', '') || 'dashboard'}`}
              >
                <Icon className="w-5 h-5" />
                <span>{item.label}</span>
              </a>
            </Link>
          );
        })}
      </nav>

      {/* Bot Status */}
      <div className="p-4 border-t border-sidebar-border">
        <div className={cn(
          "flex items-center space-x-3 p-3 rounded-lg",
          botStatus?.instagram_connected 
            ? "bg-green-50 dark:bg-green-900/20" 
            : "bg-red-50 dark:bg-red-900/20"
        )}>
          <div className={cn(
            "w-3 h-3 rounded-full animate-pulse",
            botStatus?.instagram_connected ? "bg-green-500" : "bg-red-500"
          )}></div>
          <div>
            <p className={cn(
              "text-sm font-medium",
              botStatus?.instagram_connected 
                ? "text-green-700 dark:text-green-400" 
                : "text-red-700 dark:text-red-400"
            )}>
              {botStatus?.instagram_connected ? "Bot Active" : "Bot Inactive"}
            </p>
            <p className={cn(
              "text-xs",
              botStatus?.instagram_connected 
                ? "text-green-600 dark:text-green-500" 
                : "text-red-600 dark:text-red-500"
            )}>
              {botStatus?.instagram_connected ? "Connected to Instagram" : "Disconnected"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
