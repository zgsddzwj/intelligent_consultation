import { Layout, Card, Typography } from 'antd'

const { Header, Content } = Layout
const { Title } = Typography

export default function DoctorDashboard() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
        <h1 style={{ margin: 0, lineHeight: '64px' }}>智能医疗管家平台 - 医生端</h1>
      </Header>
      <Content style={{ padding: '24px' }}>
        <Card>
          <Title level={2}>医生工作台</Title>
          <p>医生端功能开发中...</p>
        </Card>
      </Content>
    </Layout>
  )
}

