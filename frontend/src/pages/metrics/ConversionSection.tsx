import {
  Box,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import type { components } from "../../api/schema";

type Step = components["schemas"]["ConversionStepRead"];

/** A rate as the app shows it: one decimal, or "—" when no application reached the step. */
export const formatRate = (rate: number | null) => (rate === null ? "—" : `${rate.toFixed(1)}%`);

/** The conversion from each stage to the next one: a table and a chart of its rates. */
export function ConversionSection({ name, steps }: { name: string; steps: Step[] }) {
  return (
    <>
      <TableContainer>
        <Table size="small" aria-label={name}>
          <TableHead>
            <TableRow>
              <TableCell>From</TableCell>
              <TableCell>To</TableCell>
              <TableCell align="right">Reached from</TableCell>
              <TableCell align="right">Reached to</TableCell>
              <TableCell align="right">Rate</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {steps.map((step) => (
              <TableRow key={step.from_stage}>
                <TableCell>{step.from_stage}</TableCell>
                <TableCell>{step.to_stage}</TableCell>
                <TableCell align="right">{step.reached_from}</TableCell>
                <TableCell align="right">{step.reached_to}</TableCell>
                <TableCell align="right">
                  <Box sx={{ display: "inline-flex", alignItems: "center", gap: 1.25 }}>
                    {step.rate !== null && (
                      <LinearProgress
                        aria-hidden
                        variant="determinate"
                        value={step.rate}
                        sx={{
                          width: 64,
                          height: 4,
                          borderRadius: 1,
                          display: { xs: "none", md: "block" },
                        }}
                      />
                    )}
                    {formatRate(step.rate)}
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Box sx={{ height: (theme) => theme.spacing(30) }}>
        <BarChart
          xAxis={[{ data: steps.map((step) => `${step.from_stage} → ${step.to_stage}`) }]}
          yAxis={[{ min: 0, max: 100 }]}
          series={[
            {
              data: steps.map((step) => step.rate),
              label: "Rate",
              valueFormatter: (rate) => formatRate(rate),
            },
          ]}
        />
      </Box>
    </>
  );
}
