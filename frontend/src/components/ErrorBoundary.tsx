import { Component, ErrorInfo, ReactNode } from 'react'
import { Button, Result, Typography } from 'antd'
import { ReloadOutlined, HomeOutlined, BugOutlined } from '@ant-design/icons'

const { Paragraph, Text } = Typography

interface ErrorBoundaryProps {
  children: ReactNode
  /** 自定义fallback */
  fallback?: ReactNode
  /** 错误上报回调 */
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorId: string
}

/**
 * 错误边界组件
 * 捕获子组件树中的JavaScript错误，展示优雅的错误UI
 * 并提供重试和返回首页的操作
 */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorId: '',
    }
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
      errorId: `ERR-${Date.now().toString(36).toUpperCase()}`,
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[ErrorBoundary] 捕获到错误:', error, errorInfo)

    // 调用错误回调（如上报到监控系统）
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          padding: '24px',
          background: 'var(--background-light)',
        }}>
          <Result
            status="error"
            title={
              <span style={{ fontSize: '24px', fontWeight: 700 }}>
                页面出错了 😔
              </span>
            }
            subTitle={
              <div style={{ maxWidth: '460px' }}>
                <Paragraph style={{ color: '#666', fontSize: '14px', lineHeight: 1.7 }}>
                  抱歉，页面遇到了一些问题。我们的技术团队已收到此错误报告。
                </Paragraph>
                
                {/* 错误详情（开发环境显示） */}
                {import.meta.env.DEV && this.state.error && (
                  <div style={{
                    marginTop: '16px',
                    padding: '16px',
                    borderRadius: '12px',
                    background: '#fff2f0',
                    border: '1px solid #ffccc7',
                    textAlign: 'left',
                  }}>
                    <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginBottom: '8px' }}>
                      <BugOutlined /> 错误详情 (仅开发环境可见):
                    </Text>
                    <code style={{
                      display: 'block',
                      padding: '10px',
                      background: '#fff',
                      borderRadius: '6px',
                      fontSize: '12px',
                      color: '#cf1322',
                      overflowX: 'auto',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-all',
                    }}>
                      {this.state.error.message}
                    </code>
                    <Text type="secondary" style={{ fontSize: '11px', display: 'block', marginTop: '8px' }}>
                      错误ID: {this.state.errorId}
                    </Text>
                  </div>
                )}
              </div>
            }
            extra={[
              <Button
                key="retry"
                type="primary"
                icon={<ReloadOutlined />}
                onClick={this.handleRetry}
                size="large"
                style={{ borderRadius: '10px', minWidth: '120px' }}
              >
                重试加载
              </Button>,
              <Button
                key="home"
                icon={<HomeOutlined />}
                onClick={this.handleGoHome}
                size="large"
                style={{ borderRadius: '10px', minWidth: '120px' }}
              >
                返回首页
              </Button>,
            ]}
            style={{
              padding: '48px',
              borderRadius: '20px',
              background: '#fff',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)',
              maxWidth: '560px',
            }}
          />
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
