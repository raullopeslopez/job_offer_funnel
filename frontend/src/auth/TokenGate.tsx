import type { ReactNode } from "react";
import { TokenForm } from "./TokenForm";
import { useToken } from "./token";

export function TokenGate({ children }: { children: ReactNode }) {
  return useToken() ? children : <TokenForm />;
}
