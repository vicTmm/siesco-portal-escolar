import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva("inline-flex items-center justify-center gap-2 rounded-lg text-sm font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600", {
  variants: { variant: { default: "bg-emerald-800 text-white hover:bg-emerald-900", outline: "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50", ghost: "text-slate-600 hover:bg-slate-100", destructive: "bg-red-50 text-red-700 hover:bg-red-100" }, size: { default: "h-11 px-4", sm: "h-9 px-3", icon: "h-10 w-10" } },
  defaultVariants: { variant: "default", size: "default" },
});
function Button({ className, variant, size, asChild = false, ...props }: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}
export { Button, buttonVariants };
