import GroupsOutlined from "@mui/icons-material/GroupsOutlined";
import MarkEmailReadOutlined from "@mui/icons-material/MarkEmailReadOutlined";
import WorkOutlined from "@mui/icons-material/WorkOutlined";
import WorkspacePremiumOutlined from "@mui/icons-material/WorkspacePremiumOutlined";
import {
  Alert,
  Box,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useSearchParams } from "react-router";
import { api } from "../../api/client";
import { ConversionSection, formatRate } from "./ConversionSection";
import { OfferQualityPanel } from "./OfferQualityPanel";
import { StatTile } from "./StatTile";

async function fetchMetrics() {
  const [conversion, byChannel, pipeline] = await Promise.all([
    api.GET("/api/v1/metrics/conversion"),
    api.GET("/api/v1/metrics/conversion-by-channel"),
    api.GET("/api/v1/metrics/pipeline"),
  ]);
  if (!conversion.data || !byChannel.data || !pipeline.data) {
    throw conversion.error ?? byChannel.error ?? pipeline.error;
  }
  return { conversion: conversion.data, byChannel: byChannel.data, pipeline: pipeline.data };
}

type View = "offers" | "funnel";

// Two views (specs/ui/metrics.feature): the offer quality, first, and the funnel.
export function MetricsPage() {
  const [params, setParams] = useSearchParams();
  const view: View = params.get("view") === "funnel" ? "funnel" : "offers";

  return (
    <>
      <Typography variant="h4" component="h1" gutterBottom>
        Metrics
      </Typography>
      <ToggleButtonGroup
        exclusive
        size="small"
        value={view}
        aria-label="Metrics view"
        onChange={(_event, chosen: View | null) => {
          if (chosen) setParams(chosen === "funnel" ? { view: chosen } : {});
        }}
        sx={{ mb: 3 }}
      >
        <ToggleButton value="offers">Offers</ToggleButton>
        <ToggleButton value="funnel">Funnel</ToggleButton>
      </ToggleButtonGroup>
      {view === "offers" ? <OfferQualityPanel /> : <FunnelMetrics />}
    </>
  );
}

function FunnelMetrics() {
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: fetchMetrics });

  if (metrics.isPending) return null;
  if (metrics.isError) {
    return <Alert severity="error">The metrics could not be loaded</Alert>;
  }

  const { conversion, byChannel, pipeline } = metrics.data;
  // Every application reaches the first stage, so its count is the number of applications.
  if (conversion.steps[0]?.reached_from === 0) {
    return <Alert severity="info">No applications yet: add one to see your metrics</Alert>;
  }

  const inStage = (name: string) =>
    pipeline.stages.find(({ stage }) => stage === name)?.applications ?? 0;
  const responseRate = conversion.steps.find(({ from_stage }) => from_stage === "applied")?.rate;

  return (
    <>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", md: "repeat(4, minmax(0, 1fr))" },
          gap: { xs: 1.5, md: 2 },
          mb: 4,
        }}
      >
        <StatTile
          icon={WorkOutlined}
          tone="indigo"
          label="Active"
          value={pipeline.total}
          hint="applications in the pipeline"
        />
        <StatTile
          icon={GroupsOutlined}
          tone="amber"
          label="Interviewing"
          value={inStage("interviewing")}
          hint="applications"
        />
        <StatTile
          icon={MarkEmailReadOutlined}
          tone="teal"
          label="Response rate"
          value={formatRate(responseRate ?? null)}
          hint="applied → screening"
        />
        <StatTile
          icon={WorkspacePremiumOutlined}
          tone="green"
          label="Offers"
          value={inStage("offer")}
          hint="applications"
        />
      </Box>
      <Stack spacing={4}>
        <Section name="Conversion by stage">
          <ConversionSection name="Conversion by stage" steps={conversion.steps} />
        </Section>

        <Section name="Conversion by channel">
          {byChannel.channels.map(({ channel, steps }) => (
            <Box key={channel} sx={{ mb: 2 }}>
              <Typography variant="h6" component="h3">
                {channel}
              </Typography>
              <ConversionSection name={`Conversion for ${channel}`} steps={steps} />
            </Box>
          ))}
        </Section>

        <Section name="Active pipeline">
          <Typography color="text.secondary" gutterBottom>
            {pipeline.total} active applications in total
          </Typography>
          <TableContainer>
            <Table size="small" aria-label="Active pipeline">
              <TableHead>
                <TableRow>
                  <TableCell>Stage</TableCell>
                  <TableCell align="right">Applications</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {pipeline.stages.map(({ stage, applications }) => (
                  <TableRow key={stage}>
                    <TableCell>{stage}</TableCell>
                    <TableCell align="right">{applications}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <Box sx={{ height: (theme) => theme.spacing(30) }}>
            <BarChart
              xAxis={[{ data: pipeline.stages.map(({ stage }) => stage) }]}
              series={[
                { data: pipeline.stages.map(({ applications }) => applications), label: "Active" },
              ]}
            />
          </Box>
        </Section>
      </Stack>
    </>
  );
}

function Section({ name, children }: { name: string; children: ReactNode }) {
  const id = name.toLowerCase().replaceAll(" ", "-");
  return (
    <Box component="section" aria-labelledby={id}>
      <Typography id={id} variant="h5" component="h2" gutterBottom>
        {name}
      </Typography>
      {children}
    </Box>
  );
}
