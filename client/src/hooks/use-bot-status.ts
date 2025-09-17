import { useQuery } from "@tanstack/react-query";
import type { BotStatus } from "@shared/schema";

export function useBotStatus() {
  return useQuery<BotStatus>({
    queryKey: ["/api/bot/status"],
    refetchInterval: 5000, // Refresh every 5 seconds
  });
}
