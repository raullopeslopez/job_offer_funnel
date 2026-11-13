import type { SvgIconComponent } from "@mui/icons-material";
import BusinessOutlined from "@mui/icons-material/BusinessOutlined";
import HubOutlined from "@mui/icons-material/HubOutlined";
import InboxOutlined from "@mui/icons-material/InboxOutlined";
import InsightsOutlined from "@mui/icons-material/InsightsOutlined";
import TravelExploreOutlined from "@mui/icons-material/TravelExploreOutlined";
import WorkOutlined from "@mui/icons-material/WorkOutlined";

export type NavItem = { path: string; label: string; icon: SvgIconComponent };

// One entry per screen, in two groups (docs/frontend.md).
export const navGroups: { label: string; items: NavItem[] }[] = [
  {
    label: "Offers",
    items: [
      { path: "/inbox", label: "Inbox", icon: InboxOutlined },
      { path: "/profiles", label: "Profiles", icon: TravelExploreOutlined },
      { path: "/sources", label: "Sources", icon: HubOutlined },
    ],
  },
  {
    label: "Pipeline",
    items: [
      { path: "/applications", label: "Applications", icon: WorkOutlined },
      { path: "/metrics", label: "Metrics", icon: InsightsOutlined },
      { path: "/companies", label: "Companies", icon: BusinessOutlined },
    ],
  },
];
