import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import MainLayout from "./components/layout/MainLayout";
import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import Assistant from "./pages/Assistant";
import GraphExplorer from "./pages/GraphExplorer";
import RoutingAnalytics from "./pages/RoutingAnalytics";
import Monitoring from "./pages/Monitoring";
import Evaluation from "./pages/Evaluation";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<MainLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/assistant" element={<Assistant />} />
            <Route path="/graph" element={<GraphExplorer />} />
            <Route path="/routing" element={<RoutingAnalytics />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/evaluation" element={<Evaluation />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
