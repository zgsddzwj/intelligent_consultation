import { Avatar } from 'antd'
import { RobotOutlined } from '@ant-design/icons'

export default function TypingIndicator() {
  return (
    <div
      className="animate-fade-in"
      style={{
        display: 'flex',
        gap: '12px',
        marginTop: '20px',
        padding: '0 16px',
        alignItems: 'flex-start',
      }}
    >
      <Avatar
        icon={<RobotOutlined />}
        style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)',
          flexShrink: 0,
        }}
        size={40}
      />
      <div
        style={{
          padding: '14px 20px',
          borderRadius: '20px 20px 20px 4px',
          background: 'var(--background-white)',
          boxShadow: 'var(--shadow-sm)',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          border: '1px solid var(--border-color)',
          minWidth: '72px',
        }}
      >
        {/* 打字动画点 */}
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: 'var(--primary-color)',
            display: 'inline-block',
            animation: 'typingDot 1.4s ease-in-out infinite',
            animationDelay: '0ms',
          }}
        />
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: 'var(--primary-light)',
            display: 'inline-block',
            animation: 'typingDot 1.4s ease-in-out infinite',
            animationDelay: '200ms',
          }}
        />
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: 'var(--primary-300)',
            display: 'inline-block',
            animation: 'typingDot 1.4s ease-in-out infinite',
            animationDelay: '400ms',
          }}
        />
      </div>
    </div>
  )
}
