"use client";
import * as React from "react";
import * as Primitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
export const Dialog = Primitive.Root;
export const DialogTitle = Primitive.Title;
export const DialogDescription = Primitive.Description;
export function DialogContent({ children }: { children: React.ReactNode }) {
  return <Primitive.Portal><Primitive.Overlay className="dialog-overlay" /><Primitive.Content className="dialog-content">
    {children}<Primitive.Close className="dialog-close" aria-label="Fechar formulário"><X size={20} /></Primitive.Close>
  </Primitive.Content></Primitive.Portal>;
}
