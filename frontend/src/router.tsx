import { createBrowserRouter, Navigate } from "react-router";
import { Layout } from "./layout/Layout";
import { ApplicationDetailPage } from "./pages/applications/ApplicationDetailPage";
import { ApplicationsPage } from "./pages/applications/ApplicationsPage";
import { CompaniesPage } from "./pages/companies/CompaniesPage";
import { InboxPage } from "./pages/inbox/InboxPage";
import { MetricsPage } from "./pages/metrics/MetricsPage";
import { SearchesPage } from "./pages/searches/SearchesPage";
import { SourcesPage } from "./pages/sources/SourcesPage";

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/inbox" replace /> },
      { path: "inbox", element: <InboxPage /> },
      { path: "profiles", element: <SearchesPage /> },
      { path: "sources", element: <SourcesPage /> },
      { path: "applications", element: <ApplicationsPage /> },
      { path: "applications/:applicationId", element: <ApplicationDetailPage /> },
      { path: "metrics", element: <MetricsPage /> },
      { path: "companies", element: <CompaniesPage /> },
    ],
  },
]);
