import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "next-themes";
import Dashboard from "@/pages/dashboard";
import Automation from "@/pages/automation";
import Content from "@/pages/content";
import Settings from "@/pages/settings";
import Analytics from "@/pages/analytics";
import UserManagement from "@/pages/user-management";
import ActivityLogs from "@/pages/activity-logs";
import Sidebar from "@/components/layout/sidebar";
import Header from "@/components/layout/header";
import NotFound from "@/pages/not-found";

function Router() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Header />
        <Switch>
          <Route path="/" component={Dashboard} />
          <Route path="/automation" component={Automation} />
          <Route path="/users" component={UserManagement} />
          <Route path="/content" component={Content} />
          <Route path="/analytics" component={Analytics} />
          <Route path="/settings" component={Settings} />
          <Route path="/logs" component={ActivityLogs} />
          <Route component={NotFound} />
        </Switch>
      </main>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
