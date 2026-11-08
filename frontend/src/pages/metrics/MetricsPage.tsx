import {
  Alert,
  Box,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { api } from "../../api/client";
import { ConversionSection } from "./ConversionSection";

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

export function MetricsPage() {
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: fetchMetrics });

  const title = (
    <Typography variant="h4" component="h1" gutterBottom>
      Metrics
    </Typography>
  );
  if (metrics.isPending) return title;
  if (metrics.isError) {
    return (
      <>
        {title}
        <Alert severity="error">The metrics could not be loaded</Alert>
      </>
    );
  }

  const { conversion, byChannel, pipeline } = metrics.data;
  // Every application reaches the first stage, so its count is the number of applications.
  if (conversion.steps[0]?.reached_from === 0) {
    return (
      <>
        {title}
        <Alert severity="info">No applications yet: add one to see your metrics</Alert>
      </>
    );
  }

  return (
    <>
      {title}
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
