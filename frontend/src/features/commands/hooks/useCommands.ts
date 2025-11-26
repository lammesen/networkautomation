import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { JobCreateResponse } from '@/types'
import type { RunCommandsPayload } from '../types'

export function useCommandSuggestions(platform: string) {
  return useQuery({
    queryKey: ['commandSuggestions', platform],
    queryFn: () => apiClient.getCommandSuggestions(platform),
    enabled: !!platform,
  })
}

export function useRunCommands() {
  return useMutation({
    mutationFn: (data: RunCommandsPayload) => apiClient.runCommands(data),
  })
}

export type { JobCreateResponse }
