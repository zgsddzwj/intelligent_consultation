import { Flex, Typography } from 'antd'
import {
  MedicineBoxOutlined,
  HeartOutlined,
  BulbOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons'

const { Text } = Typography

export interface QuickSuggestion {
  icon: React.ReactNode
  text: string
  color: string
}

interface WelcomeScreenProps {
  quickSuggestions?: QuickSuggestion[]
  onQuickSuggestion?: (text: string) => void
}

export default function WelcomeScreen({ quickSuggestions, onQuickSuggestion }: WelcomeScreenProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        minHeight: '400px',
        padding: '32px 24px',
      }}
    >
      {/* Logo */}
      <div
        style={{
          width: '72px',
          height: '72px',
          borderRadius: '20px',
          background: 'linear-gradient(135deg, #2563eb 0%, #0d9488 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '20px',
          boxShadow: '0 8px 24px rgba(37, 99, 235, 0.2)',
        }}
      >
        <MedicineBoxOutlined style={{ fontSize: '32px', color: 'white' }} />
      </div>

      {/* 标题 */}
      <h2
        style={{
          color: 'var(--text-primary)',
          fontSize: '22px',
          fontWeight: 700,
          marginBottom: '8px',
          textAlign: 'center',
        }}
      >
        欢迎使用智能医疗管家
      </h2>

      {/* 描述 */}
      <p
        style={{
          color: 'var(--text-secondary)',
          fontSize: '14px',
          textAlign: 'center',
          lineHeight: 1.6,
          marginBottom: '28px',
          maxWidth: '420px',
        }}
      >
        我是您的 AI 医疗助手，可以帮您解答健康问题、提供医疗建议。
        请描述您的症状或咨询问题，我会基于专业医疗知识为您提供帮助。
      </p>

      {/* 快捷问题 */}
      {quickSuggestions && quickSuggestions.length > 0 && onQuickSuggestion && (
        <div style={{ marginBottom: '28px', width: '100%', maxWidth: '480px' }}>
          <Text type="secondary" style={{ fontSize: '12px', display: 'block', marginBottom: '12px', textAlign: 'center' }}>
            常见问题快捷入口
          </Text>
          <Flex wrap gap="small" justify="center" style={{ width: '100%' }}>
            {quickSuggestions.map((item, idx) => (
              <div
                key={idx}
                onClick={() => onQuickSuggestion(item.text)}
                style={{
                  cursor: 'pointer',
                  padding: '10px 16px',
                  borderRadius: '12px',
                  background: 'var(--background-white)',
                  border: '1px solid var(--border-color)',
                  transition: 'all 0.25s ease',
                  textAlign: 'center',
                  minWidth: '110px',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = `${item.color}40`
                  e.currentTarget.style.boxShadow = `0 4px 12px ${item.color}15`
                  e.currentTarget.style.transform = 'translateY(-2px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-color)'
                  e.currentTarget.style.boxShadow = 'none'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                <div style={{ fontSize: '20px', marginBottom: '4px', color: item.color }}>{item.icon}</div>
                <Text style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 500 }}>{item.text}</Text>
              </div>
            ))}
          </Flex>
        </div>
      )}

      {/* 功能标签 */}
      <Flex wrap gap="large" justify="center" style={{ marginBottom: '20px' }}>
        {[
          { icon: <HeartOutlined />, text: '健康咨询', color: '#dc2626' },
          { icon: <BulbOutlined />, text: '医学知识', color: '#d97706' },
          { icon: <MedicineBoxOutlined />, text: '用药指导', color: '#16a34a' },
        ].map((item, idx) => (
          <div key={idx} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '24px', color: item.color, marginBottom: '4px' }}>{item.icon}</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>{item.text}</div>
          </div>
        ))}
      </Flex>

      {/* 免责提示 */}
      <div
        style={{
          background: 'var(--info-bg)',
          padding: '10px 20px',
          borderRadius: '10px',
          border: '1px solid var(--primary-100)',
          maxWidth: '440px',
        }}
      >
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
          <SafetyCertificateOutlined style={{ color: 'var(--primary-color)' }} />
          <span><strong>温馨提示：</strong>本平台仅提供参考信息，不替代医生诊断。如有紧急情况，请立即就医。</span>
        </div>
      </div>
    </div>
  )
}
