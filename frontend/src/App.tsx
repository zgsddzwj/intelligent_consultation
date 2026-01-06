import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from 'antd'
import DoctorDashboard from './pages/DoctorDashboard'
import PatientPortal from './pages/PatientPortal'
import AdminPanel from './pages/AdminPanel'
import KnowledgeGraph from './pages/KnowledgeGraph'

const { Content } = Layout

function App() {
  return (
    <BrowserRouter>
      <Layout style={{ minHeight: '100vh' }}>
        <Content>
          <Routes>
            <Route path="/" element={<PatientPortal />} />
            <Route path="/doctor" element={<DoctorDashboard />} />
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="/knowledge-graph" element={<KnowledgeGraph />} />
          </Routes>
        </Content>
      </Layout>
    </BrowserRouter>
  )
}

export default App

