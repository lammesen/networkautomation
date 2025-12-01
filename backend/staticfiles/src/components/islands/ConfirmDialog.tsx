import * as React from "react";
import { AlertTriangle, Info, Loader2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "default" | "destructive" | "warning";
  onConfirm: () => void | Promise<void>;
  onCancel?: () => void;
  loading?: boolean;
  children?: React.ReactNode;
};

const variantConfig = {
  default: {
    icon: Info,
    iconClass: "text-primary",
    confirmVariant: "default" as const,
  },
  destructive: {
    icon: AlertTriangle,
    iconClass: "text-destructive",
    confirmVariant: "destructive" as const,
  },
  warning: {
    icon: AlertTriangle,
    iconClass: "text-amber-500",
    confirmVariant: "default" as const,
  },
};

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  onConfirm,
  onCancel,
  loading = false,
  children,
}: ConfirmDialogProps) {
  const [isLoading, setIsLoading] = React.useState(false);
  const config = variantConfig[variant];
  const Icon = config.icon;

  const handleConfirm = async () => {
    setIsLoading(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch (error) {
      console.error("Confirm action failed:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    onCancel?.();
    onOpenChange(false);
  };

  const showLoading = loading || isLoading;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-start gap-3">
            <div
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
                variant === "destructive" && "bg-destructive/10",
                variant === "warning" && "bg-amber-500/10",
                variant === "default" && "bg-primary/10"
              )}
            >
              <Icon className={cn("h-5 w-5", config.iconClass)} />
            </div>
            <div className="flex-1">
              <AlertDialogTitle>{title}</AlertDialogTitle>
              {description && (
                <AlertDialogDescription>{description}</AlertDialogDescription>
              )}
            </div>
          </div>
        </AlertDialogHeader>

        {children && <div className="py-4">{children}</div>}

        <AlertDialogFooter>
          <AlertDialogCancel asChild>
            <Button variant="outline" onClick={handleCancel} disabled={showLoading}>
              {cancelLabel}
            </Button>
          </AlertDialogCancel>
          <AlertDialogAction asChild>
            <Button
              variant={config.confirmVariant}
              onClick={handleConfirm}
              disabled={showLoading}
            >
              {showLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {confirmLabel}
            </Button>
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

// Hook for managing confirm dialog state
export function useConfirmDialog() {
  const [state, setState] = React.useState<{
    open: boolean;
    title: string;
    description?: string;
    variant?: ConfirmDialogProps["variant"];
    confirmLabel?: string;
    onConfirm?: () => void | Promise<void>;
  }>({
    open: false,
    title: "",
  });

  const confirm = React.useCallback(
    (options: {
      title: string;
      description?: string;
      variant?: ConfirmDialogProps["variant"];
      confirmLabel?: string;
    }): Promise<boolean> => {
      return new Promise((resolve) => {
        setState({
          ...options,
          open: true,
          onConfirm: () => resolve(true),
        });
      });
    },
    []
  );

  const close = React.useCallback(() => {
    setState((prev) => ({ ...prev, open: false }));
  }, []);

  const dialogProps: ConfirmDialogProps = {
    open: state.open,
    onOpenChange: (open) => setState((prev) => ({ ...prev, open })),
    title: state.title,
    description: state.description,
    variant: state.variant,
    confirmLabel: state.confirmLabel,
    onConfirm: state.onConfirm || (() => {}),
    onCancel: close,
  };

  return { confirm, close, dialogProps };
}

export default ConfirmDialog;
