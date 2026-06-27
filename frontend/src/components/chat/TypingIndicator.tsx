import { Avatar } from 'antd'
import { RobotOutlined } from '@ant-design/icons'

export default function TypingIndicator() {
  return (
    <div
      className="animate-fade-in"
      style={{
        display: 'flex',
        gap: '10px',
        marginBottom: '16px',
        padding: '0 24px',
        alignItems: 'flex-start',
      }}
    >
      <Avatar
        icon={<RobotOutlined />}
        style={{
          background: 'linear-gradient(135deg, #2563eb 0%, #0d9488 100%)',
          boxShadow: '0 2px 8px rgba(37, 99, 235, 0.2)',
          flexShrink: 0,
        }}
        size={36}
      />
      <div
        style={{
          padding: '14px 18px',
          borderRadius: '14px 14px 14px 4px',
          background: 'var(--background-white)',
          boxShadow: 'var(--shadow-sm)',
          display: 'flex',
          alignItems: 'center',
          gap: '5px',
          border: '1px solid var(--border-color)',
          minWidth: '60px',
        }}
      >
        {/* 打字动画点 */}
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            style={{
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              background: i === 0 ? 'var(--primary-color)' : i === 1 ? 'var(--primary-400)' : 'var(--primary-300)',
              display: 'inline-block',
              animation: 'typingDot 1.4s ease-in-out infinite',
              animationDelay: `${i * 200}ms`,
            }}
          />
        ))}
      </div>
    </div>
  )
}
