import { Space, Flex, Typography } from 'antd'
import {
  MedicineBoxOutlined,
  HeartOutlined,
  BulbOutlined,
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
        padding: '40px',
      }}
    >
      <div
        style={{
          width: '120px',
          height: '120px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '24px',
          boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3)',
        }}
      >
        <MedicineBoxOutlined style={{ fontSize: '48px', color: 'white' }} />
      </div>

      <h2
        style={{
          color: '#333',
          fontSize: '24px',
          fontWeight: '600',
          marginBottom: '12px',
          textAlign: 'center',
        }}
      >
        欢迎使用智能医疗管家
      </h2>

      <p
        style={{
          color: '#666',
          fontSize: '16px',
          textAlign: 'center',
          lineHeight: '1.6',
          marginBottom: '32px',
          maxWidth: '500px',
        }}
      >
        我是您的AI医疗助手，可以帮您解答健康问题、提供医疗建议。
        请描述您的症状或咨询问题，我会基于专业医疗知识为您提供帮助。
      </p>

      {quickSuggestions && quickSuggestions.length > 0 && onQuickSuggestion && (
        <div style={{ marginBottom: '28px', width: '100%', maxWidth: '520px' }}>
          <Text type="secondary" style={{ fontSize: '13px', display: 'block', marginBottom: '14px', textAlign: 'center' }}>
            💡 常见问题快捷入口
          </Text>
          <Flex wrap gap="middle" justify="center" style={{ width: '100%' }}>
            {quickSuggestions.map((item, idx) => (
              <div
                key={idx}
                onClick={() => onQuickSuggestion(item.text)}
                style={{
                  cursor: 'pointer',
                  padding: '12px 20px',
                  borderRadius: '16px',
                  background: 'var(--background-white)',
                  border: '1px solid var(--border-color)',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                  textAlign: 'center',
                  minWidth: '120px',
                }}
              >
                <div style={{ fontSize: '24px', marginBottom: '6px', color: item.color }}>{item.icon}</div>
                <Text style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 500 }}>{item.text}</Text>
              </div>
            ))}
          </Flex>
        </div>
      )}

      <Space direction="vertical" size="large">
        <Space wrap size="large">
          <div style={{ textAlign: 'center' }}>
            <HeartOutlined style={{ fontSize: '32px', color: '#ff4d4f', marginBottom: '8px' }} />
            <div style={{ color: '#666', fontSize: '14px' }}>健康咨询</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <BulbOutlined style={{ fontSize: '32px', color: '#faad14', marginBottom: '8px' }} />
            <div style={{ color: '#666', fontSize: '14px' }}>医学知识</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <MedicineBoxOutlined style={{ fontSize: '32px', color: '#52c41a', marginBottom: '8px' }} />
            <div style={{ color: '#666', fontSize: '14px' }}>用药指导</div>
          </div>
        </Space>

        <div
          style={{
            background: 'rgba(102, 126, 234, 0.1)',
            padding: '16px 24px',
            borderRadius: '12px',
            border: '1px solid rgba(102, 126, 234, 0.2)',
          }}
        >
          <div style={{ fontSize: '14px', color: '#666', textAlign: 'center' }}>
            💡 <strong>温馨提示：</strong>本平台仅提供参考信息，不替代医生诊断。如有紧急情况，请立即就医。
          </div>
        </div>
      </Space>
    </div>
  )
}
