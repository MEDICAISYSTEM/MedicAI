import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Appointments from "./pages/Appointments";
import Patients from "./pages/Patients";
import Conversations from "./pages/Conversations";
import Availability from "./pages/Availability";
import Alerts from "./pages/Alerts";
import SuperAdmin from "./pages/SuperAdmin";
import Layout from "./components/Layout";

const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem("medicai_token");
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

const SuperAdminRoute = ({ children }) => {
  const token = localStorage.getItem("medicai_token");
  const admin = JSON.parse(localStorage.getItem("medicai_admin") || "{}");
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  if (!admin.is_super_admin) {
    return <Navigate to="/" replace />;
  }
  
  return children;
};

function App() {
  return (
    <>
      <Toaster 
        position="top-right" 
        richColors 
        closeButton
        toastOptions={{
          style: {
            fontFamily: 'Inter, sans-serif',
          },
        }}
      />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="appointments" element={<Appointments />} />
            <Route path="patients" element={<Patients />} />
            <Route path="conversations" element={<Conversations />} />
            <Route path="availability" element={<Availability />} />
            <Route path="alerts" element={<Alerts />} />
            <Route 
              path="superadmin" 
              element={
                <SuperAdminRoute>
                  <SuperAdmin />
                </SuperAdminRoute>
              } 
            />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
