import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Moon, Sun, Bell } from "lucide-react";
import { useTheme } from "next-themes";

const pageTitles: Record<string, { title: string; description: string }> = {
  "/": {
    title: "Dashboard",
    description: "Monitor and control your Instagram automation bot"
  },
  "/automation": {
    title: "Automation",
    description: "Configure and manage automation modules"
  },
  "/content": {
    title: "Content & Tags",
    description: "Manage hashtags, locations, and DM templates"
  },
  "/settings": {
    title: "Settings",
    description: "Configure bot settings and preferences"
  },
};

export default function Header() {
  const [location] = useLocation();
  const { theme, setTheme } = useTheme();
  
  const pageInfo = pageTitles[location] || { title: "Dashboard", description: "Instagram Bot Control Panel" };

  return (
    <header className="bg-card border-b border-border p-6" data-testid="header">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{pageInfo.title}</h1>
          <p className="text-muted-foreground">{pageInfo.description}</p>
        </div>
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            data-testid="theme-toggle"
          >
            <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </Button>
          <Button variant="ghost" size="icon" data-testid="notifications">
            <Bell className="h-5 w-5" />
          </Button>
          <div className="flex items-center space-x-2 p-2 bg-secondary rounded-lg">
            <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
              <span className="text-xs font-medium text-primary-foreground">AD</span>
            </div>
            <span className="text-sm font-medium">Admin</span>
          </div>
        </div>
      </div>
    </header>
  );
}
