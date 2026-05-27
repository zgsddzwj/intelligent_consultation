/**
 * 组件库统一导出
 *
 * 使用方式：
 * import { DataTable, ConfirmModal, EmptyState } from '@/components'
 */

export { DataTable } from './DataTable'
export { ConfirmModal } from './ConfirmModal'
export { EmptyState } from './EmptyState'
export { ErrorBoundary } from './ErrorBoundary'
export { PageLoading } from './PageLoading'
export { ResponsiveContainer } from './ResponsiveContainer'
export { SkeletonLoader } from './SkeletonLoader'

// Chat组件
export {
  ChatMessage,
  ChatInput,
  TypingIndicator,
  WelcomeScreen,
} from './chat'

export type { MessageStatus, ChatStreamEvent } from './chat'
