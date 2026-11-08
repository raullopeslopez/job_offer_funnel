import { createBrowserRouter } from "react-router";
import { Layout } from "./layout/Layout";
import { ApplicationDetailPage } from "./pages/applications/ApplicationDetailPage";
import { ApplicationsPage } from "./pages/applications/ApplicationsPage";
import { Home } from "./pages/Home";
import { InboxPage } from "./pages/inbox/InboxPage";
import { MetricsPage } from "./pages/metrics/MetricsPage";
import { SearchesPage } from "./pages/searches/SearchesPage";

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: "inbox", element: <InboxPage /> },
      { path: "searches", element: <SearchesPage /> },
      { path: "applications", element: <ApplicationsPage /> },
      { path: "applications/:applicationId", element: <ApplicationDetailPage /> },
      { path: "metrics", element: <MetricsPage /> },
    ],
  },
]);
