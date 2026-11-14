import {
  Alert,
  Box,
  Link,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router";
import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { mono } from "../../theme";
import { DISCARD_REASON_LABELS } from "../inbox/discardReasons";
import { formatRate } from "./ConversionSection";
import { CriteriaChanges } from "./CriteriaChanges";
import { SuggestedExclusions } from "./SuggestedExclusions";

type Quality = components["schemas"]["OfferQualityRead"];
type Week = components["schemas"]["WeekQualityRead"];

type Card = {
  label: string;
  value: string;
  sentence: string;
  trend: (number | null)[];
  to: string;
};

/** The four key results of specs/ui/metrics.feature, "—" when there is nothing to show. */
export function qualityCards(quality: Quality): Card[] {
  const { total, weeks } = quality;
  const trend = (figure: (week: Week) => number | null) => weeks.map(figure);
  return [
    {
      label: "Precision",
      value: formatRate(total.precision),
      sentence: `${total.promoted_from_pending} promoted of ${total.decided} decided from Pending`,
      trend: trend((week) => week.precision),
      to: "/inbox",
    },
    {
      label: "Losses",
      value: formatRate(total.losses),
      sentence: `${total.rescued_near_misses} rescued of ${total.reviewed_near_misses} near misses reviewed · ${quality.near_misses_left} to review`,
      trend: trend((week) => week.losses),
      to: "/inbox?status=filtered",
    },
    {
      label: "Flow",
      value: total.fitting === 0 ? "—" : `${quality.fitting_per_week.toFixed(1)}/week`,
      sentence: `${total.fitting} new offers that fit in 4 weeks`,
      trend: trend((week) => week.fitting),
      to: "/sources",
    },
    {
      label: "Real result",
      value: total.promoted === 0 ? "—" : `${total.applied} applied`,
      sentence: `${total.answered} answered of ${total.promoted} promoted`,
      trend: trend((week) => week.applied),
      to: "/applications",
    },
  ];
}

function Trend({ values }: { values: (number | null)[] }) {
  const highest = Math.max(1, ...values.map((value) => value ?? 0));
  return (
    <Box aria-hidden sx={{ display: "flex", alignItems: "flex-end", gap: "3px", height: 20 }}>
      {values.map((value, week) => (
        <Box
          // biome-ignore lint/suspicious/noArrayIndexKey: the 4 weeks are fixed, in order
          key={week}
          sx={{
            width: 8,
            height: `${Math.max(8, ((value ?? 0) / highest) * 100)}%`,
            bgcolor: value === null ? "divider" : "text.primary",
            opacity: week === values.length - 1 ? 1 : 0.4,
            borderRadius: "2px",
          }}
        />
      ))}
    </Box>
  );
}

/** How the offer triager does, once it triaged an offer you decided on; null before. */
function TriageFigures({ quality }: { quality: Quality }) {
  const { total, weeks } = quality;
  if (total.suggested_decided + total.triaged_discarded === 0) return null;
  const figures = [
    {
      label: "Precision",
      value: formatRate(total.triager_precision),
      sentence: `${total.suggested_discarded} right of ${total.suggested_decided} suggested discards you decided`,
      trend: weeks.map((week) => week.triager_precision),
    },
    {
      label: "Misses",
      value: formatRate(total.triager_misses),
      sentence: `${total.missed_discards} missed of ${total.triaged_discarded} triaged offers you discarded`,
      trend: weeks.map((week) => week.triager_misses),
    },
  ];
  return (
    <Box component="section" aria-labelledby="ai-triage" sx={{ mb: 4 }}>
      <Typography id="ai-triage" variant="h6" component="h3" gutterBottom>
        The AI triage
      </Typography>
      <Paper
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
          gap: "1px",
          bgcolor: "divider",
          overflow: "hidden",
        }}
      >
        {figures.map((figure) => (
          <Box
            key={figure.label}
            sx={{ display: "grid", gap: 1, p: 2, bgcolor: "background.paper" }}
          >
            <Typography variant="body2" color="text.secondary">
              {figure.label}
            </Typography>
            <Typography
              component="div"
              sx={{ fontFamily: mono, fontSize: "1.75rem", fontWeight: 500, lineHeight: 1.1 }}
            >
              {figure.value}
            </Typography>
            <Trend values={figure.trend} />
            <Typography variant="caption" color="text.secondary">
              {figure.sentence}
            </Typography>
          </Box>
        ))}
      </Paper>
    </Box>
  );
}

function DiscardBars({ reasons }: { reasons: Quality["discard_reasons"] }) {
  if (reasons.length === 0) {
    return <Typography color="text.secondary">No discards in the last 4 weeks.</Typography>;
  }
  const highest = Math.max(...reasons.map(({ offers }) => offers));
  return (
    <Box component="ul" aria-label="Why you discard" sx={{ listStyle: "none", p: 0, m: 0 }}>
      {reasons.map(({ reason, offers }, index) => (
        <Box
          component="li"
          key={reason}
          sx={{ display: "grid", gridTemplateColumns: "10rem 1fr 3rem", gap: 1, mb: 0.75 }}
        >
          <Typography variant="body2">{DISCARD_REASON_LABELS[reason]}</Typography>
          <Box
            sx={{
              height: 12,
              alignSelf: "center",
              width: `${(offers / highest) * 100}%`,
              bgcolor: index === 0 ? "text.primary" : "action.disabled",
              borderRadius: "2px",
            }}
          />
          <Typography variant="body2" sx={{ fontFamily: mono, textAlign: "right" }}>
            {offers}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}

export function OfferQualityPanel() {
  const quality = useQuery({
    queryKey: ["offers", "quality"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/offers/quality");
      if (error) throw error;
      return data;
    },
  });

  if (quality.isPending) return null;
  if (quality.isError) {
    return <Alert severity="error">The offer quality could not be loaded</Alert>;
  }

  return (
    <Box component="section" aria-labelledby="offer-quality">
      <Typography id="offer-quality" variant="h5" component="h2">
        Offer quality
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        Is what reaches Pending worth your time, and does what is worth your time reach Pending?
        Last 4 weeks.
      </Typography>
      <Paper
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(4, 1fr)" },
          gap: "1px",
          bgcolor: "divider",
          overflow: "hidden",
          mb: 4,
        }}
      >
        {qualityCards(quality.data).map((card) => (
          <Link
            key={card.label}
            component={RouterLink}
            to={card.to}
            underline="none"
            color="inherit"
            aria-label={card.label}
            sx={{ display: "grid", gap: 1, p: 2, bgcolor: "background.paper" }}
          >
            <Typography variant="body2" color="text.secondary">
              {card.label}
            </Typography>
            <Typography
              component="div"
              sx={{ fontFamily: mono, fontSize: "1.75rem", fontWeight: 500, lineHeight: 1.1 }}
            >
              {card.value}
            </Typography>
            <Trend values={card.trend} />
            <Typography variant="caption" color="text.secondary">
              {card.sentence}
            </Typography>
          </Link>
        ))}
      </Paper>

      <TriageFigures quality={quality.data} />

      <CriteriaChanges />

      <Typography variant="h6" component="h3" gutterBottom>
        Why you discard
      </Typography>
      <Box sx={{ mb: 4 }}>
        <DiscardBars reasons={quality.data.discard_reasons} />
        <SuggestedExclusions />
      </Box>

      <Typography variant="h6" component="h3" gutterBottom>
        By source
      </Typography>
      <Table size="small" aria-label="By source">
        <TableHead>
          <TableRow>
            <TableCell>Source</TableCell>
            <TableCell align="right">Imported</TableCell>
            <TableCell align="right">Fit</TableCell>
            <TableCell align="right">Promoted</TableCell>
            <TableCell align="right">Discarded</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {quality.data.sources.map((source) => (
            <TableRow key={source.source}>
              <TableCell>{source.source}</TableCell>
              <TableCell align="right">{source.imported}</TableCell>
              <TableCell align="right">{source.fitting}</TableCell>
              <TableCell align="right">{source.promoted}</TableCell>
              <TableCell align="right">{source.discarded}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}
