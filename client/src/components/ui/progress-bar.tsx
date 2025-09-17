import { cn } from "@/lib/utils";

interface ProgressBarProps {
  value: number;
  className?: string;
  color?: "blue" | "red" | "purple" | "green";
}

const colorClasses = {
  blue: "bg-blue-500",
  red: "bg-red-500", 
  purple: "bg-purple-500",
  green: "bg-green-500",
};

export default function ProgressBar({ value, className, color = "blue" }: ProgressBarProps) {
  return (
    <div className={cn("w-full bg-background rounded-full h-2", className)}>
      <div 
        className={cn("h-2 rounded-full transition-all duration-300", colorClasses[color])}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}
