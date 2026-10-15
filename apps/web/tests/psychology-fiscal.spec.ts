import { test, expect, type Page } from "@playwright/test";
async function login(page: Page, email: string) {
  await page.goto("/");
  await page.getByLabel("E-mail", { exact: true }).fill(email);
  await page
    .getByLabel("Senha", { exact: true })
    .fill(process.env.DEMO_PASSWORD!);
  await page.getByRole("button", { name: "Entrar no portal" }).click();
  await expect(
    page.getByRole("button", { name: "Sair", exact: true }),
  ).toBeVisible();
}
async function logout(page: Page) {
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page.getByLabel("E-mail", { exact: true })).toBeVisible();
}
async function nav(page: Page, name: string) {
  await page
    .getByRole("navigation")
    .getByRole("button", { name, exact: true })
    .click();
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
}

test("psicólogo registra atendimento e evolução; direção consulta e secretaria não acessa", async ({
  page,
}) => {
  await login(page, "psychologist@aurora.example.com");
  await expect(
    page.getByRole("heading", { name: "Psicologia escolar", exact: true }),
  ).toBeVisible();
  const options = page.getByLabel("Aluno do acompanhamento").locator("option");
  await expect(options).not.toHaveCount(1);
  await page
    .getByLabel("Aluno do acompanhamento")
    .selectOption({ label: "Ana Lima (fictício)" });
  const observation = "Atendimento sintético E2E " + Date.now();
  await page.getByLabel("Data e hora do atendimento").fill("2026-02-03T10:00");
  await page.getByLabel("Observações do atendimento").fill(observation);
  await page
    .getByLabel("Análise do psicólogo")
    .fill("Análise sintética restrita");
  await page
    .getByLabel("Plano de acompanhamento")
    .fill("Retorno individual de demonstração");
  await page
    .getByRole("button", { name: "Registrar atendimento", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Atendimento registrado",
  );
  await page
    .getByRole("button", { name: "Consultar atendimento" })
    .first()
    .click();
  await expect(page.getByText(observation, { exact: true })).toBeVisible();
  await page
    .getByLabel("Acrescentar evolução ou retificação")
    .fill("Evolução sintética preservada no histórico");
  await page.getByRole("button", { name: "Salvar complemento" }).click();
  await expect(
    page.getByText("Evolução sintética preservada no histórico", {
      exact: true,
    }),
  ).toBeVisible();
  await logout(page);
  await login(page, "director@aurora.example.com");
  await nav(page, "Psicologia escolar");
  await page
    .getByRole("button", { name: "Consultar atendimento" })
    .first()
    .click();
  await expect(page.getByText(observation, { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Registrar atendimento", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Salvar complemento" }),
  ).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/psychology-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await logout(page);
  await login(page, "secretary@aurora.example.com");
  await expect(
    page
      .getByRole("navigation")
      .getByRole("button", { name: "Psicologia escolar", exact: true }),
  ).toHaveCount(0);
});

test("NFS-e prepara rascunho e impede emissão sem certificado, sem simular autorização", async ({
  page,
}) => {
  await login(page, "director@aurora.example.com");
  await nav(page, "Notas fiscais de serviços");
  const me = await (await page.request.get("/api/backend/me")).json(),
    base = "/api/backend/institutions/" + me.memberships[0].institution_id;
  const profile = await (
    await page.request.get(base + "/fiscal/profile")
  ).json();
  test.skip(
    profile &&
      (profile.cnpj !== "11222333000181" || profile.environment !== "test"),
    "Não alterar cadastro fiscal real",
  );
  if (!profile) {
    await page
      .getByLabel("CNPJ da escola", { exact: true })
      .fill("11222333000181");
    await page
      .getByLabel("Razão social", { exact: true })
      .fill("Escola Fiscal Sintética E2E");
    await page
      .getByLabel("Código IBGE do município emissor", { exact: true })
      .fill("3304904");
    await page.getByLabel("Série da DPS", { exact: true }).fill("1");
    await page.getByLabel("Próximo número da DPS", { exact: true }).fill("1");
    await page
      .getByLabel("Código nacional do serviço (6 dígitos)", { exact: true })
      .fill("080101");
    await page
      .getByLabel("Opção pelo Simples Nacional", { exact: true })
      .selectOption("3");
    await page.getByLabel("Regime especial", { exact: true }).selectOption("0");
    for (const label of ["Percentual total aproximado no Simples (%)"])
      await page
        .getByLabel(label, { exact: true })
        .fill(label.startsWith("Percentual") ? "6" : "0");
    await page
      .getByLabel(
        "Confirmei com o contador o enquadramento e a compatibilidade desta operação, sem retenções ou deduções.",
      )
      .check();
    await page
      .getByRole("button", { name: "Salvar cadastro fiscal", exact: true })
      .click();
    await expect(page.getByRole("status")).toContainText(
      "Cadastro fiscal salvo",
    );
  }
  await page
    .getByLabel("Aluno da nota fiscal")
    .selectOption({ label: "Ana Lima (fictício)" });
  await expect(
    page.getByLabel("Tomador — responsável verificado"),
  ).toContainText("Marina");
  const description = "Serviço sintético fiscal E2E " + Date.now();
  const fields: { [key: string]: string } = {
    "CPF/CNPJ do tomador": "52998224725",
    Competência: "2026-02-03",
    "Valor do serviço (R$)": "650,00",
    "Descrição do serviço": description,
    "CEP do tomador": "24452000",
    "Código IBGE do município do tomador": "3304904",
    "Logradouro do tomador": "Rua sintética",
    "Número do endereço": "100",
    "Bairro do tomador": "Engenho Pequeno",
  };
  for (const [label, value] of Object.entries(fields))
    await page.getByLabel(label, { exact: true }).fill(value);
  await page
    .getByRole("button", { name: "Preparar rascunho fiscal", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Rascunho fiscal preparado",
  );
  const article = page.locator("article").filter({ hasText: description });
  await expect(article).toContainText("R$ 650,00");
  page.once("dialog", (dialog) => dialog.accept());
  await article
    .getByRole("button", { name: "Emitir em homologação", exact: true })
    .click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Certificado fiscal" }),
  ).toBeVisible();
  await expect(article).toContainText("Rascunho");
  await expect(
    article.getByRole("button", { name: "Baixar XML autorizado" }),
  ).toHaveCount(0);
  await page.screenshot({
    path: "test-results/fiscal-desktop.png",
    fullPage: true,
  });
});
