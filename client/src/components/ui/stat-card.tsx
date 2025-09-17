import { Card, CardContent } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";
import ProgressBar from "./progress-bar";

interface StatCardProps {
  title: string;
  value: number;
  limit: number;
  icon: LucideIcon;
  color: "blue" | "red" | "purple" | "green";
  className?: string;
}

const colorClasses = {
  blue: "bg-blue-100 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400",
  red: "bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400",
  purple: "bg-purple-100 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400",
  green: "bg-green-100 dark:bg-green-900/20 text-green-600 dark:text-green-400",
};

export default function StatCard({ title, value, limit, icon: Icon, color, className }: StatCardProps) {
  const percentage = limit > 0 ? (value / limit) * 100 : 0;
  
  return (
    <Card className={className}>
      <CardContent className="p-6">
        <div className="flex items-center space-x-4">
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
            <Icon className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
            <p className="text-xs text-green-600 dark:text-green-400">
              of {limit} limit
            </p>
            <ProgressBar 
              value={percentage} 
              className="mt-2" 
              color={color}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
