import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CatalogView } from "@/components/catalog";

const mocks = vi.hoisted(() => ({ api: vi.fn(), allRows: vi.fn() }));
vi.mock("@/lib/api", () => ({ ...mocks, ApiError: class ApiError extends Error { status = 401; } }));
const props = { resource: "students", base: "institutions/demo", role: "director", expired: vi.fn() };

describe("Cadastro integrado à API", () => {
  beforeEach(() => { vi.clearAllMocks(); mocks.api.mockResolvedValue([]); mocks.allRows.mockResolvedValue([]); });

  it("mostra carregamento antes da resposta", () => {
    mocks.api.mockReturnValue(new Promise(() => {}));
    render(<CatalogView {...props} />);
    expect(screen.getByRole("status", { name: "Carregando registros" })).toBeVisible();
  });

  it("oferece recuperação de erro sem apresentar sucesso", async () => {
    mocks.api.mockRejectedValueOnce(new Error("Serviço indisponível"));
    render(<CatalogView {...props} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Serviço indisponível");
    await userEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(await screen.findByText("Tudo pronto para começar")).toBeVisible();
  });

  it("perfil sem escrita não recebe controles de edição", async () => {
    mocks.api.mockResolvedValue([{ id: "1", name: "Aluno Fictício", birth_date: "2015-01-01" }]);
    render(<CatalogView {...props} role="coordinator" />);
    expect(await screen.findByText("Aluno Fictício")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Cadastrar aluno" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar Aluno Fictício" })).not.toBeInTheDocument();
  });

  it("envia cadastro e preserva mensagem de validação do servidor", async () => {
    render(<CatalogView {...props} />);
    await screen.findByText("Tudo pronto para começar");
    await userEvent.click(screen.getByRole("button", { name: "Cadastrar aluno" }));
    await userEvent.type(screen.getByLabelText("Nome completo *"), "Aluno de Teste");
    await userEvent.type(screen.getByLabelText("Data de nascimento *"), "2015-02-01");
    mocks.api.mockRejectedValueOnce(new Error("Registro duplicado"));
    await userEvent.click(screen.getByRole("button", { name: "Salvar cadastro" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Registro duplicado");
    expect(screen.getByRole("dialog")).toBeVisible();
    expect(mocks.api).toHaveBeenLastCalledWith("institutions/demo/students", { method: "POST", body: JSON.stringify({ name: "Aluno de Teste", birth_date: "2015-02-01" }) });
    await userEvent.click(screen.getByRole("button", { name: "Salvar cadastro" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(await screen.findByText("Cadastro realizado com sucesso.")).toBeVisible();
  });

  it("usa PUT ao editar sem enviar campos internos", async () => {
    mocks.api.mockResolvedValue([{ id: "1", institution_id: "demo", school_id: "s", name: "Aluno Fictício", birth_date: "2015-01-01" }]);
    render(<CatalogView {...props} />);
    await userEvent.click(await screen.findByRole("button", { name: "Editar Aluno Fictício" }));
    const input = screen.getByLabelText("Nome completo *");
    await userEvent.clear(input); await userEvent.type(input, "Nome Corrigido");
    await userEvent.click(screen.getByRole("button", { name: "Salvar cadastro" }));
    expect(mocks.api).toHaveBeenCalledWith("institutions/demo/students/1", { method: "PUT", body: JSON.stringify({ name: "Nome Corrigido", birth_date: "2015-01-01" }) });
  });
});
