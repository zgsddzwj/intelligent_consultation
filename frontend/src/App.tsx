import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout, Spin } from 'antd'
import { ErrorBoundary } from './components/ErrorBoundary'

// 使用 React.lazy 实现路由级代码分割，减少首屏加载时间
const PatientPortal = lazy(() => import('./pages/PatientPortal'))
const DoctorDashboard = lazy(() => import('./pages/DoctorDashboard'))
const AdminPanel = lazy(() => import('./pages/AdminPanel'))
const KnowledgeGraph = lazy(() => import('./pages/KnowledgeGraph'))

const { Content } = Layout

// 统一的加载 fallback 组件
function PageLoading() {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh'
    }}>
      <Spin size="large" tip="页面加载中..." />
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Layout style={{ minHeight: '100vh' }}>
        <Content>
          <Suspense fallback={<PageLoading />}>
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<PatientPortal />} />
                <Route path="/doctor" element={<DoctorDashboard />} />
                <Route path="/admin" element={<AdminPanel />} />
                <Route path="/knowledge-graph" element={<KnowledgeGraph />} />
              </Routes>
            </ErrorBoundary>
          </Suspense>
        </Content>
      </Layout>
    </BrowserRouter>
  )
}

export default App
