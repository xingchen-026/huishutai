/** 从 axios 错误 / 普通 Error 中提取可展示的中文文案 */
export function getErrorMessage(error: unknown, fallback = '网络错误，请稍后再试'): string {
  const responseMessage = (error as { response?: { data?: { message?: string } } })?.response?.data
    ?.message
  if (typeof responseMessage === 'string' && responseMessage) return responseMessage

  if (error instanceof Error && error.message && !error.message.startsWith('Request failed')) {
    return error.message
  }
  return fallback
}
