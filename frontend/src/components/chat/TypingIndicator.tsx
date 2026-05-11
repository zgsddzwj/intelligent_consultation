import { Avatar, Spin } from 'antd'
import { RobotOutlined } from '@ant-design/icons'

export default function TypingIndicator() {
  return (
    <div
      style={{
        display: 'flex',
        gap: '12px',
        marginTop: '20px',
        padding: '0 16px',
      }}
    >
      <Avatar
        icon={<RobotOutlined />}
        style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)',
        }}
        size={40}
      />
      <div
        style={{
          padding: '16px 20px',
          borderRadius: '20px 20px 20px 4px',
          background: '#ffffff',
          boxShadow: '0 2px 12px rgba(0, 0, 0, 0.08)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          border: '1px solid rgba(0, 0, 0, 0.05)',
        }}
      >
        <Spin size="small" style={{ color: '#667eea' }} />
        <span style={{ color: '#666', fontSize: '14px' }}>AI正在思考中...</span>
      </div>
    </div>
  )
}
