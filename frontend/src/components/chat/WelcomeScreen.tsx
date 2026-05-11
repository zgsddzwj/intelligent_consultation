import { Space } from 'antd'
import {
  MedicineBoxOutlined,
  HeartOutlined,
  BulbOutlined,
} from '@ant-design/icons'

export default function WelcomeScreen() {
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
      {/* 平台图标 */}
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

      {/* 标题 */}
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

      {/* 描述 */}
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

      {/* 功能特性 */}
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

        {/* 温馨提示 */}
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
