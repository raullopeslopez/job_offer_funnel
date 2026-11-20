import { Avatar, Box, type Theme } from "@mui/material";
import { useState } from "react";
import type { Tone } from "../theme";

export const LOGO_URL = (domain: string) =>
  `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`;

/** `https://www.acme.com/jobs` -> `acme.com`; no website (or an invalid one) -> `null`. */
export function domainOf(website: string | null | undefined): string | null {
  if (!website) return null;
  try {
    const url = new URL(/^https?:\/\//i.test(website) ? website : `https://${website}`);
    return url.hostname.replace(/^www\./, "") || null;
  } catch {
    return null;
  }
}

const TONES: Tone[] = ["blue", "indigo", "teal", "amber", "green", "red", "orange"];

export function toneForName(name: string): Tone {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0;
  return TONES[Math.abs(h) % TONES.length] ?? "blue";
}

const ring = (theme: Theme) => ({
  boxShadow: `inset 0 0 0 1px ${(theme.vars ?? theme).palette.divider}`,
});

type Props = { name: string; domain?: string | null; size?: 32 | 28 };

// Decorative company mark: logo when there is a domain, tinted initial otherwise or if the image fails.
export function CompanyAvatar({ name, domain, size = 32 }: Props) {
  const [failed, setFailed] = useState(false);
  const tone = toneForName(name);
  const box = {
    width: size,
    height: size,
    borderRadius: "30%",
    flexShrink: 0,
  };

  if (domain && !failed) {
    return (
      <Box
        component="img"
        src={LOGO_URL(domain)}
        alt=""
        aria-hidden
        onError={() => setFailed(true)}
        sx={(theme) => ({
          ...box,
          ...ring(theme),
          objectFit: "contain",
          // In px: a padding in % is a share of the container's width, not of the avatar's.
          boxSizing: "border-box",
          p: `${Math.round(size * 0.14)}px`,
          bgcolor: "background.paper",
        })}
      />
    );
  }
  return (
    <Avatar
      variant="rounded"
      aria-hidden
      sx={(theme) => ({
        ...box,
        ...ring(theme),
        fontSize: size * 0.42,
        fontWeight: 600,
        bgcolor: (theme.vars ?? theme).palette.tone[tone].bg,
        color: (theme.vars ?? theme).palette.tone[tone].fg,
      })}
    >
      {name.trim().charAt(0).toUpperCase()}
    </Avatar>
  );
}
