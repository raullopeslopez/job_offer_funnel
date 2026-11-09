import type { SvgIconComponent } from "@mui/icons-material";
import HomeOutlined from "@mui/icons-material/HomeOutlined";
import InboxOutlined from "@mui/icons-material/InboxOutlined";
import InsightsOutlined from "@mui/icons-material/InsightsOutlined";
import SettingsOutlined from "@mui/icons-material/SettingsOutlined";
import TravelExploreOutlined from "@mui/icons-material/TravelExploreOutlined";
import VisibilityOutlined from "@mui/icons-material/VisibilityOutlined";
import WorkOutlined from "@mui/icons-material/WorkOutlined";

// One entry per screen, added by the PR of each screen (docs/frontend.md).
export const navItems: { path: string; label: string; icon: SvgIconComponent }[] = [
  { path: "/", label: "Home", icon: HomeOutlined },
  { path: "/inbox", label: "Inbox", icon: InboxOutlined },
  { path: "/searches", label: "Searches", icon: TravelExploreOutlined },
  { path: "/watched-companies", label: "Watched companies", icon: VisibilityOutlined },
  { path: "/applications", label: "Applications", icon: WorkOutlined },
  { path: "/metrics", label: "Metrics", icon: InsightsOutlined },
  { path: "/settings", label: "Settings", icon: SettingsOutlined },
];
