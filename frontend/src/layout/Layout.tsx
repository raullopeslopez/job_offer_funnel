import DarkModeOutlined from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlined from "@mui/icons-material/LightModeOutlined";
import MenuOutlined from "@mui/icons-material/MenuOutlined";
import {
  AppBar,
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Tooltip,
  Typography,
  useColorScheme,
  useMediaQuery,
} from "@mui/material";
import type { Theme } from "@mui/material/styles";
import { useState } from "react";
import { NavLink, Outlet } from "react-router";
import { navItems } from "./navItems";

const DRAWER_WIDTH = 240;

export function Layout() {
  const isMobile = useMediaQuery((theme: Theme) => theme.breakpoints.down("md"));
  const [navOpen, setNavOpen] = useState(false);
  const { colorScheme, setMode } = useColorScheme();
  const dark = colorScheme === "dark";
  const ThemeIcon = dark ? LightModeOutlined : DarkModeOutlined;
  const themeLabel = dark ? "Light theme" : "Dark theme";

  const nav = (
    <Box
      component="nav"
      aria-label="Main"
      sx={{ display: "flex", flexDirection: "column", height: "100%" }}
    >
      <Toolbar sx={{ minHeight: 64, px: 3 }}>
        <Typography variant="h6" component="span" sx={{ fontWeight: 600 }}>
          Job Offer Funnel
        </Typography>
      </Toolbar>
      <List sx={{ flex: 1 }}>
        {navItems.map(({ path, label, icon: Icon }) => (
          <ListItemButton
            key={path}
            component={NavLink}
            to={path}
            end
            onClick={() => setNavOpen(false)}
            sx={{
              "& .MuiListItemIcon-root": { color: "text.secondary" },
              "&.active .MuiListItemIcon-root": { color: "primary.main" },
            }}
          >
            <ListItemIcon sx={{ minWidth: 32 }}>
              <Icon aria-hidden="true" sx={{ fontSize: 20 }} />
            </ListItemIcon>
            <ListItemText primary={label} />
          </ListItemButton>
        ))}
      </List>
      <Divider />
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2,
          py: 1.5,
        }}
      >
        <Typography variant="body2" color="text.secondary">
          {themeLabel}
        </Typography>
        <Tooltip title={themeLabel}>
          <IconButton aria-label={themeLabel} onClick={() => setMode(dark ? "light" : "dark")}>
            <ThemeIcon aria-hidden="true" fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: { md: "flex" } }}>
      {isMobile ? (
        <>
          <AppBar
            position="sticky"
            color="inherit"
            elevation={0}
            sx={{ borderBottom: 1, borderColor: "divider", bgcolor: "background.paper" }}
          >
            <Toolbar sx={{ minHeight: 56, px: 1 }} disableGutters>
              <Tooltip title="Open navigation">
                <IconButton aria-label="Open navigation" onClick={() => setNavOpen(true)}>
                  <MenuOutlined aria-hidden="true" />
                </IconButton>
              </Tooltip>
              <Typography variant="h6" component="span" sx={{ fontWeight: 600, ml: 1 }}>
                Job Offer Funnel
              </Typography>
            </Toolbar>
          </AppBar>
          <Drawer
            variant="temporary"
            open={navOpen}
            onClose={() => setNavOpen(false)}
            ModalProps={{ keepMounted: false }}
            sx={{ "& .MuiDrawer-paper": { width: DRAWER_WIDTH } }}
          >
            {nav}
          </Drawer>
        </>
      ) : (
        <Drawer
          variant="permanent"
          sx={{ width: DRAWER_WIDTH, flexShrink: 0, "& .MuiDrawer-paper": { width: DRAWER_WIDTH } }}
        >
          {nav}
        </Drawer>
      )}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          minWidth: 0,
          maxWidth: 1280,
          boxSizing: "border-box",
          px: { xs: 2, md: 6 },
          pt: { xs: 2.5, md: 5 },
          pb: 12,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}
