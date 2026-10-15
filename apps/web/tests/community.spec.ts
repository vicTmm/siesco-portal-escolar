import { test, expect, type Page } from "@playwright/test";
const password = process.env.DEMO_PASSWORD;
async function login(page: Page, email: string) {
  await page.goto("/");
  await page.getByLabel("E-mail", { exact: true }).fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Entrar no portal" }).click();
  await expect(
    page.getByRole("button", { name: "Sair", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".stat-skeleton")).toHaveCount(0);
}
async function navigate(page: Page, title: string) {
  await page
    .getByRole("navigation")
    .getByRole("button", { name: title, exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: title, exact: true }),
  ).toBeVisible();
}
test("mural: publicação, resposta familiar e confirmação; PDF e hash público", async ({
  page,
  browser,
}) => {
  test.skip(!password, "Configure a senha de demonstração");
  await login(page, "director@aurora.example.com");
  const me = await (await page.request.get("/api/backend/me")).json();
  const base = "/api/backend/institutions/" + me.memberships[0].institution_id;
  const groups = await (await page.request.get(base + "/classes")).json();
  const year = groups[0].academic_year;
  const title = "Autorização E2E " + Date.now();
  await navigate(page, "Mural e autorizações");
  await page.getByLabel("Título", { exact: true }).fill(title);
  await page
    .getByLabel("Mensagem", { exact: true })
    .fill("Autoriza participação na atividade sintética de demonstração?");
  await page.getByLabel("Tipo", { exact: true }).selectOption("authorization");
  await page.getByLabel("Ano letivo", { exact: true }).fill(String(year));
  await page.getByRole("button", { name: "Publicar no mural" }).click();
  await expect(
    page.getByRole("heading", { name: title, exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await login(page, "guardian@aurora.example.com");
  await navigate(page, "Mural e autorizações");
  const article = page
    .locator("article")
    .filter({ has: page.getByRole("heading", { name: title, exact: true }) });
  await article
    .getByRole("button", { name: "Autorizo", exact: true })
    .first()
    .click();
  await expect(
    article.getByText(/Leitura confirmada · Autorizo/).first(),
  ).toBeVisible();
  const portal = await (await page.request.get(base + "/portal")).json();
  const student =
    portal.students.find((s: { name: string }) =>
      s.name.startsWith("Ana Lima"),
    ) || portal.students[0];
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await login(page, "director@aurora.example.com");
  await navigate(page, "Documentos escolares");
  const enrollments = await (
    await page.request.get(base + "/enrollments")
  ).json();
  const studentYear = enrollments.find(
    (e: { student_id: string }) => e.student_id === student.id,
  ).academic_year;
  await page.getByLabel("Aluno", { exact: true }).selectOption(student.id);
  await page
    .getByLabel("Ano letivo", { exact: true })
    .fill(String(studentYear));
  const issuedResponse = page.waitForResponse(
    (r) => r.url().endsWith("/documents") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Emitir PDF", exact: true }).click();
  const issued = await (await issuedResponse).json();
  await expect(page.getByRole("status")).toContainText("Documento emitido");
  const download = page.waitForEvent("download");
  await page.locator(`article[data-document-id="${issued.id}"]`).getByRole("button",{name:"Baixar PDF"}).click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/\.pdf$/);
  const publicPage = await browser.newPage();
  await publicPage.goto(
    new URL(new URL(issued.verification_url).pathname, page.url()).href,
  );
  await expect(
    publicPage.getByText("Registro válido", { exact: true }),
  ).toBeVisible();
  await publicPage
    .getByLabel("Conferir arquivo PDF")
    .setInputFiles((await file.path())!);
  await expect(publicPage.getByRole("status")).toHaveText(
    "Arquivo corresponde ao documento emitido.",
  );
  await publicPage.close();
  await page.screenshot({
    path: "test-results/documents-desktop.png",
    fullPage: false,
  });
  await navigate(page, "Serviços escolares");
  await page.getByLabel("Serviço", { exact: true }).selectOption("tickets");
  await page
    .getByLabel("Título", { exact: true })
    .fill("Atendimento E2E " + Date.now());
  await page.getByLabel("Setor", { exact: true }).fill("Secretaria");
  await page
    .getByLabel("Solicitação", { exact: true })
    .fill("Atualizar contato sintético");
  await page
    .getByRole("button", { name: "Salvar registro", exact: true })
    .click();
  await expect(page.locator("article").first()).toContainText(
    "Atualizar contato sintético",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.getByRole("button", { name: "Abrir menu" })).toBeVisible();
  await page.screenshot({
    path: "test-results/services-mobile.png",
    fullPage: false,
  });
});
