import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Account from "./pages/Account";
import Editor from "./pages/Editor";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import PublicPage from "./pages/PublicPage";
import Register from "./pages/Register";

// Top-level paths here must be in the backend's RESERVED_HANDLES
// (app/services/page_service.py), since every other path is a page handle.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/edit" element={<Editor />} />
        <Route path="/account" element={<Account />} />
      </Route>

      <Route path="/:handle" element={<PublicPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
