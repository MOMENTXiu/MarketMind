import { ApiError } from './errors'
import { apiClient, requestDirect } from './client'
import type { CustomerSuggestionRequest, CustomerSuggestionResponse } from './types'

export async function generateCustomerSuggestion(
  payload: CustomerSuggestionRequest
): Promise<CustomerSuggestionResponse> {
  const response = await requestDirect<CustomerSuggestionResponse>(
    apiClient.post('/api/analysis/customer-suggestions', payload)
  )
  if (!response.success) {
    throw new ApiError({ message: '生成建议失败', raw: response })
  }
  return response
}