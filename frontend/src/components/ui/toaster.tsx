import { Toaster as Sonner } from "sonner";

import { useTheme } from "../../theme/ThemeProvider";

/** Toast notifications. Call `toast.success(...)` / `toast.error(...)` from "sonner" anywhere. */
export function Toaster() {
  const { resolved } = useTheme();
  return (
    <Sonner
      theme={resolved}
      position="bottom-right"
      closeButton
      toastOptions={{
        classNames: {
          toast:
            "!rounded-xl !border !border-border !bg-popover !text-popover-foreground !shadow-lifted !font-sans",
          description: "!text-muted-foreground",
          closeButton: "!border-border !bg-popover !text-muted-foreground",
        },
      }}
    />
  );
}
