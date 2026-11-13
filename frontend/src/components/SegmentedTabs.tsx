import { Box, Tab, Tabs } from "@mui/material";
import { mono } from "../theme";

export type SegmentedItem<T extends string> = { value: T; label: string; count: number };

type Props<T extends string> = {
  items: SegmentedItem<T>[];
  value: T;
  onChange: (value: T) => void;
  "aria-label": string;
};

// A pill of tabs with their counts; the active one in ink. Tab roles and arrow keys from MUI.
export function SegmentedTabs<T extends string>({
  items,
  value,
  onChange,
  "aria-label": ariaLabel,
}: Props<T>) {
  return (
    <Tabs
      value={value}
      onChange={(_, next: T) => onChange(next)}
      aria-label={ariaLabel}
      variant="scrollable"
      scrollButtons={false}
      sx={{
        display: "inline-flex",
        minHeight: 0,
        p: 0.5,
        borderRadius: 999,
        border: 1,
        borderColor: "divider",
        bgcolor: "background.paper",
        "& .MuiTabs-indicator": { display: "none" },
      }}
    >
      {items.map((item) => (
        <Tab
          key={item.value}
          value={item.value}
          disableRipple
          label={
            <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: 1 }}>
              {item.label}
              <Box component="span" sx={{ fontFamily: mono, opacity: 0.75 }}>
                {item.count}
              </Box>
            </Box>
          }
          sx={{
            minHeight: 44,
            px: 2,
            borderRadius: 999,
            color: "text.secondary",
            "&.Mui-selected": { bgcolor: "primary.main", color: "primary.contrastText" },
            "&.Mui-focusVisible": { outline: "2px solid", outlineColor: "primary.main" },
          }}
        />
      ))}
    </Tabs>
  );
}
