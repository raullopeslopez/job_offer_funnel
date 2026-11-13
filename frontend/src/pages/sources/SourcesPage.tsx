import DeleteOutlineOutlined from "@mui/icons-material/DeleteOutlineOutlined";
import EditOutlined from "@mui/icons-material/EditOutlined";
import HubOutlined from "@mui/icons-material/HubOutlined";
import VisibilityOffOutlined from "@mui/icons-material/VisibilityOffOutlined";
import { Box, Button, Stack, Typography } from "@mui/material";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link as RouterLink } from "react-router";
import { api } from "../../api/client";
import { CompanyAvatar } from "../../components/CompanyAvatar";
import { RowAction } from "../../components/RowActions";
import { Meta, Sep } from "../../components/TwoLineCell";
import type { Source } from "../../theme";
import { ImportJobBoardDialog } from "../inbox/ImportJobBoardDialog";
import { DeleteJobBoardDialog } from "../settings/DeleteJobBoardDialog";
import { JobBoardDialog } from "../settings/JobBoardDialog";
import { ImportWatchedCompanyDialog } from "../watched-companies/ImportWatchedCompanyDialog";
import { StopWatchingDialog } from "../watched-companies/StopWatchingDialog";
import { WatchCompanyDialog } from "../watched-companies/WatchCompanyDialog";
import { SourceBlock, SourceItem } from "./SourceBlock";
import type { JobBoard, WatchedCompany } from "./types";

// The API's largest page: the blocks need every job board to split them by import method.
const PAGE_LIMIT = 100;

const NO_JOB_BOARDS = "No job boards";

type Method = JobBoard["import_method"];
type Block = { kind: Exclude<Source, "watched">; title: string; text: string };

const BOARD_BLOCKS: Record<Method, Block> = {
  api: {
    kind: "api",
    title: "API import",
    text: "The app asks the board for its recent offers and keeps them all; your profiles decide which fit.",
  },
  rss: {
    kind: "rss",
    title: "RSS import",
    text: "The board's RSS feed is read once for each job title in your profiles.",
  },
  email: {
    kind: "email",
    title: "Email alerts",
    text: "You create the alert on the board; the app reads the emails that reach the alerts mailbox. Offers arrive without a description.",
  },
  none: {
    kind: "manual",
    title: "Added by hand, with a generated search",
    text: "No automatic import. The app writes the search for each profile; you open it and add what you like to the inbox.",
  },
};

function importedFrom(jobBoard: JobBoard): string {
  if (jobBoard.email_alert) return `${jobBoard.email_alert} alerts`;
  return jobBoard.feed ?? jobBoard.import_method;
}

// Where offers come from, in five blocks by how they reach the inbox (specs/ui/sources.feature).
export function SourcesPage() {
  const queryClient = useQueryClient();
  // "new" opens the form empty; a job board opens it to edit that job board.
  const [editing, setEditing] = useState<JobBoard | "new" | null>(null);
  const [deleting, setDeleting] = useState<JobBoard | null>(null);
  const [importingBoard, setImportingBoard] = useState<JobBoard | null>(null);
  const [watching, setWatching] = useState(false);
  const [importingCompany, setImportingCompany] = useState<WatchedCompany | null>(null);
  const [stopping, setStopping] = useState<WatchedCompany | null>(null);

  // The API lists the job boards alphabetically and the watched companies by name.
  const jobBoards = useQuery({
    queryKey: ["job-boards", "all"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/job-boards", {
        params: { query: { limit: PAGE_LIMIT } },
      });
      if (error) throw error;
      return data.items;
    },
  });
  const companies = useQuery({
    queryKey: ["watched-companies"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/watched-companies");
      if (error) throw error;
      return data;
    },
  });

  // The generated searches depend on the job boards.
  const refreshJobBoards = async () => {
    await queryClient.invalidateQueries({ queryKey: ["job-boards"] });
    await queryClient.invalidateQueries({ queryKey: ["searches"] });
  };
  const refreshCompanies = () => queryClient.invalidateQueries({ queryKey: ["watched-companies"] });

  const boardBlock = (method: Method) => {
    const { kind, title, text } = BOARD_BLOCKS[method];
    const boards = (jobBoards.data ?? []).filter(({ import_method }) => import_method === method);
    return (
      <SourceBlock
        kind={kind}
        title={title}
        text={text}
        empty={jobBoards.isPending ? null : NO_JOB_BOARDS}
      >
        {boards.map((board) => (
          <SourceItem
            key={board.id}
            primary={board.name}
            secondary={
              <Meta mono>
                {method === "none"
                  ? board.syntax
                  : `${board.syntax} · imported from ${importedFrom(board)}`}
              </Meta>
            }
            actions={
              <>
                {(method === "api" || method === "rss") && (
                  <Button size="small" variant="outlined" onClick={() => setImportingBoard(board)}>
                    Import now
                  </Button>
                )}
                {method === "none" && (
                  <Button
                    size="small"
                    variant="outlined"
                    component={RouterLink}
                    to="/profiles"
                    aria-label={`Searches of “${board.name}” in Profiles`}
                  >
                    Searches
                  </Button>
                )}
                <RowAction
                  icon={EditOutlined}
                  label={`Edit “${board.name}”`}
                  onClick={() => setEditing(board)}
                />
                <RowAction
                  icon={DeleteOutlineOutlined}
                  label={`Delete “${board.name}”`}
                  onClick={() => setDeleting(board)}
                />
              </>
            }
          />
        ))}
      </SourceBlock>
    );
  };

  return (
    <>
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        sx={{ justifyContent: "space-between", alignItems: { md: "flex-end" }, mb: 5 }}
      >
        <Box>
          <Typography variant="h4" component="h1" sx={{ mb: 1 }}>
            Sources
          </Typography>
          <Typography sx={{ color: "text.secondary" }}>
            Where offers come from, by how they reach the inbox. Automatic sources are checked every
            6 hours.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} sx={{ flexShrink: 0 }}>
          <Button variant="outlined" onClick={() => setWatching(true)}>
            Watch a company
          </Button>
          <Button variant="contained" onClick={() => setEditing("new")}>
            New job board
          </Button>
        </Stack>
      </Stack>

      <Stack spacing={5}>
        {boardBlock("api")}
        <SourceBlock
          kind="watched"
          title="Watched companies"
          text="Offers read straight from a company's careers page (Greenhouse, Lever or Ashby), with no job board in between."
          empty={
            companies.isPending ? null : (
              <>
                <Box component="span" sx={{ fontWeight: 500, color: "text.primary" }}>
                  No watched companies
                </Box>{" "}
                · Watch a company to import offers straight from its careers page.
              </>
            )
          }
        >
          {(companies.data ?? []).map((company) => (
            <SourceItem
              key={company.id}
              lead={<CompanyAvatar name={company.name} />}
              primary={company.name}
              secondary={
                <>
                  <Meta icon={HubOutlined}>{company.ats}</Meta>
                  <Sep />
                  <Meta mono>{company.board || "—"}</Meta>
                </>
              }
              actions={
                <>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => setImportingCompany(company)}
                  >
                    Import
                  </Button>
                  <RowAction
                    icon={VisibilityOffOutlined}
                    label={`Stop watching “${company.name}”`}
                    onClick={() => setStopping(company)}
                  />
                </>
              }
            />
          ))}
        </SourceBlock>
        {boardBlock("rss")}
        {boardBlock("email")}
        {boardBlock("none")}
      </Stack>

      {editing && (
        <JobBoardDialog
          jobBoard={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await refreshJobBoards();
          }}
        />
      )}
      <DeleteJobBoardDialog
        jobBoard={deleting}
        onClose={() => setDeleting(null)}
        onDeleted={async () => {
          setDeleting(null);
          await refreshJobBoards();
        }}
      />
      {importingBoard && (
        <ImportJobBoardDialog
          open
          jobBoard={importingBoard}
          onClose={() => setImportingBoard(null)}
        />
      )}
      {watching && (
        <WatchCompanyDialog
          onClose={() => setWatching(false)}
          onWatched={async () => {
            setWatching(false);
            await refreshCompanies();
          }}
        />
      )}
      {importingCompany && (
        <ImportWatchedCompanyDialog
          company={importingCompany}
          onClose={() => setImportingCompany(null)}
        />
      )}
      <StopWatchingDialog
        company={stopping}
        onClose={() => setStopping(null)}
        onStopped={async () => {
          setStopping(null);
          await refreshCompanies();
        }}
      />
    </>
  );
}
