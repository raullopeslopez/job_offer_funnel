import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemText,
  Toolbar,
  Typography,
} from "@mui/material";
import { NavLink, Outlet } from "react-router";
import { navItems } from "./navItems";

const DRAWER_WIDTH = 240;

export function Layout() {
  return (
    <Box sx={{ display: "flex" }}>
      <Drawer
        variant="permanent"
        sx={{ width: DRAWER_WIDTH, "& .MuiDrawer-paper": { width: DRAWER_WIDTH } }}
      >
        <Toolbar>
          <Typography variant="h6" component="span">
            Job Offer Funnel
          </Typography>
        </Toolbar>
        <List component="nav" aria-label="Main">
          {navItems.map(({ path, label }) => (
            <ListItemButton
              key={path}
              component={NavLink}
              to={path}
              end
              sx={{ "&.active": { bgcolor: "action.selected" } }}
            >
              <ListItemText primary={label} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Outlet />
      </Box>
    </Box>
  );
}
