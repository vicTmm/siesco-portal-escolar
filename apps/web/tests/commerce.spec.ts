import { test, expect } from "@playwright/test";
test("carteira registra crédito, compra com estoque e consulta familiar", async ({
  page,
}) => {
  const password = process.env.DEMO_PASSWORD!;
  async function login(email: string) {
    await page.goto("/");
    await page.getByLabel("E-mail", { exact: true }).fill(email);
    await page.getByLabel("Senha", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Entrar no portal" }).click();
    await expect(
      page.getByRole("button", { name: "Sair", exact: true }),
    ).toBeVisible();
  }
  await login("director@aurora.example.com");
  const me = await (await page.request.get("/api/backend/me")).json(),
    base = "/api/backend/institutions/" + me.memberships[0].institution_id;
  const students = await (
      await page.request.get(base + "/students?limit=100")
    ).json(),
    student = students.find((s: { name: string }) =>
      s.name.startsWith("Ana Lima"),
    );
  const before = await (
    await page.request.get(base + "/wallets/" + student.id)
  ).json();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Carteira, cantina e loja", exact: true })
    .click();
  await page
    .getByLabel("Aluno da carteira", { exact: true })
    .selectOption(student.id);
  await page.getByText("Cadastrar produto / evento", { exact: true }).click();
  const product = "Item cantina E2E " + Date.now();
  await page
    .getByLabel("Código do produto", { exact: true })
    .fill("teste-" + Date.now());
  await page.getByLabel("Nome", { exact: true }).fill(product);
  await page.getByLabel("Preço (R$)", { exact: true }).fill("5.00");
  await page.getByLabel("Estoque disponível", { exact: true }).fill("2");
  await page
    .getByRole("button", { name: "Salvar produto", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText(
    "Catálogo e estoque atualizados.",
  );
  await page
    .getByLabel("Valor recebido (R$)", { exact: true })
    .fill("10.00");
  await page
    .getByLabel("Referência / observação visível à família", { exact: true })
    .fill("Crédito fictício para teste de interface");
  await page
    .getByRole("button", { name: "Registrar crédito manual", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText(
    "Crédito manual registrado.",
  );
  await page.getByLabel("Quantidade de " + product, { exact: true }).fill("1");
  await page
    .getByRole("button", {
      name: "Confirmar compra com saldo da carteira",
      exact: true,
    })
    .click();
  await expect(page.getByRole("status")).toHaveText(
    "Operação registrada na carteira e no estoque.",
  );
  const after = await (
    await page.request.get(base + "/wallets/" + student.id)
  ).json();
  expect(after.balance_cents).toBe(before.balance_cents + 500);
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await login("guardian@aurora.example.com");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Carteira, cantina e loja", exact: true })
    .click();
  await page
    .getByLabel("Aluno da carteira", { exact: true })
    .selectOption(student.id);
  await expect(
    page.getByText("1 × " + product + " · R$ 5,00", { exact: true }),
  ).toBeVisible();
  expect(
    await page
      .getByRole("button", { name: "Registrar crédito manual", exact: true })
      .count(),
  ).toBe(0);
});
