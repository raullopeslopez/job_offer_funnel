// Single place for the funnel icon maps (all *Outlined). Keys are raw API values.
import type { SvgIconComponent } from "@mui/icons-material";
import ArrowUpwardOutlined from "@mui/icons-material/ArrowUpwardOutlined";
import BlockOutlined from "@mui/icons-material/BlockOutlined";
import CallOutlined from "@mui/icons-material/CallOutlined";
import CallReceivedOutlined from "@mui/icons-material/CallReceivedOutlined";
import DeleteOutlineOutlined from "@mui/icons-material/DeleteOutlineOutlined";
import DoNotDisturbOnOutlined from "@mui/icons-material/DoNotDisturbOnOutlined";
import EditNoteOutlined from "@mui/icons-material/EditNoteOutlined";
import ExploreOutlined from "@mui/icons-material/ExploreOutlined";
import GroupsOutlined from "@mui/icons-material/GroupsOutlined";
import HandshakeOutlined from "@mui/icons-material/HandshakeOutlined";
import HubOutlined from "@mui/icons-material/HubOutlined";
import LanguageOutlined from "@mui/icons-material/LanguageOutlined";
import RssFeedOutlined from "@mui/icons-material/RssFeedOutlined";
import ScheduleOutlined from "@mui/icons-material/ScheduleOutlined";
import SendOutlined from "@mui/icons-material/SendOutlined";
import TravelExploreOutlined from "@mui/icons-material/TravelExploreOutlined";
import UndoOutlined from "@mui/icons-material/UndoOutlined";
import VerifiedOutlined from "@mui/icons-material/VerifiedOutlined";
import VisibilityOffOutlined from "@mui/icons-material/VisibilityOffOutlined";
import VisibilityOutlined from "@mui/icons-material/VisibilityOutlined";
import WorkspacePremiumOutlined from "@mui/icons-material/WorkspacePremiumOutlined";
import type { components } from "../api/schema";

export const stageIcons: Record<string, SvgIconComponent> = {
  discovered: ExploreOutlined,
  evaluated: VisibilityOutlined,
  applied: SendOutlined,
  screening: CallOutlined,
  interviewing: GroupsOutlined,
  offer: WorkspacePremiumOutlined,
  accepted: VerifiedOutlined,
};

export const outcomeIcons: Record<string, SvgIconComponent> = {
  rejected: BlockOutlined,
  ghosted: VisibilityOffOutlined,
  withdrawn: UndoOutlined,
  offer_declined: DoNotDisturbOnOutlined,
};

export const offerStatusIcons: Record<string, SvgIconComponent> = {
  pending: ScheduleOutlined,
  discarded: DeleteOutlineOutlined,
  promoted: ArrowUpwardOutlined,
};

export const channelIcons: Record<string, SvgIconComponent> = {
  portal: LanguageOutlined,
  referral: HandshakeOutlined,
  recruiter_inbound: CallReceivedOutlined,
  direct: SendOutlined,
  networking: HubOutlined,
};

type Offer = components["schemas"]["OfferRead"];

export function offerSourceIcon(
  offer: Pick<Offer, "feed" | "job_board_name" | "watched_company_name">,
): SvgIconComponent {
  if (offer.feed) return RssFeedOutlined;
  if (offer.job_board_name || offer.watched_company_name) return TravelExploreOutlined;
  return EditNoteOutlined;
}
