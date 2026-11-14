import PlaceOutlined from "@mui/icons-material/PlaceOutlined";
import { Box } from "@mui/material";
import { offerShape, offerType } from "../theme";

type Props = { label: string };

// Where the job is: one country of the offer, or its location as published when it names
// no known country. Neutral, so it never competes with the source's color.
export function CountryTag({ label }: Props) {
  return (
    <Box
      component="span"
      title="Country"
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 0.5,
        height: offerShape.tagHeight,
        px: 1,
        borderRadius: offerShape.tagRadius,
        bgcolor: "tone.neutral.bg",
        color: "tone.neutral.fg",
        whiteSpace: "nowrap",
        ...offerType.tag,
      }}
    >
      <PlaceOutlined aria-hidden sx={{ fontSize: offerShape.iconSize }} />
      {label}
    </Box>
  );
}
