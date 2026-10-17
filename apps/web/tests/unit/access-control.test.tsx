import React from "react";
import { expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AccessControlView } from "@/components/access-control";
const mocks = vi.hoisted(() => ({ api: vi.fn(), allRows: vi.fn() }));
vi.mock("@/lib/api", () => mocks);
vi.mock("@/components/services", () => ({ Attachments: () => null }));
it("mantém o QR do aluno selecionado quando a resposta anterior chega atrasada", async () => {
  let first!: (v: unknown) => void, second!: (v: unknown) => void;
  mocks.api.mockImplementation((path: string) => {
    if (path.endsWith("/portal?limit=100")) return Promise.resolve({ students: [{ id: "a", name: "Aluno A" }, { id: "b", name: "Aluno B" }] });
    if (path.endsWith("/a/issue")) return new Promise(resolve => { first = resolve; });
    if (path.endsWith("/b/issue")) return new Promise(resolve => { second = resolve; });
    return Promise.resolve(null);
  });
  render(<AccessControlView base="institutions/demo" role="student" />);
  await screen.findByRole("option", { name: "Aluno B" });
  await userEvent.selectOptions(screen.getByLabelText("Aluno da identificação"), "a");
  await userEvent.selectOptions(screen.getByLabelText("Aluno da identificação"), "b");
  const result = (student: string) => ({ student, school: "Escola de teste", code: "sintético", qr_base64: "", expires_at: "2030-01-01T00:00:00Z" });
  await act(async () => second(result("Aluno B")));
  expect(screen.getByRole("heading", { name: "Aluno B" })).toBeVisible();
  await act(async () => first(result("Aluno A")));
  expect(screen.getByRole("heading", { name: "Aluno B" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Aluno A" })).not.toBeInTheDocument();
});
