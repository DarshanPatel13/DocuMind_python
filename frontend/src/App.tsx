import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import { AskPage } from "./pages/AskPage";
import { UploadPage } from "./pages/UploadPage";

function NavTab({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `rounded-md px-3 py-1.5 text-sm font-medium ${
          isActive ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <span className="text-lg font-bold">
            Docu<span className="text-blue-600">Mind</span>
          </span>
          <nav className="flex gap-1">
            <NavTab to="/upload" label="Upload" />
            <NavTab to="/ask" label="Ask" />
          </nav>
        </div>
      </header>

      <main className="px-4 py-8">
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/ask" element={<AskPage />} />
        </Routes>
      </main>
    </div>
  );
}
