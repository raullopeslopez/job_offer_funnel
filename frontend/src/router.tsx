import { createBrowserRouter } from "react-router";
import { Layout } from "./layout/Layout";
import { Home } from "./pages/Home";
import { InboxPage } from "./pages/inbox/InboxPage";
import { SearchesPage } from "./pages/searches/SearchesPage";

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: "inbox", element: <InboxPage /> },
      { path: "searches", element: <SearchesPage /> },
    ],
  },
]);
