import { test, expect, type Page } from "@playwright/test";

const password = process.env.DEMO_PASSWORD;
test.beforeAll(() => { if (!password) throw new Error("Defina DEMO_PASSWORD para executar os testes com seed local."); });

async function login(page: Page, email = "director@aurora.example.com") {
  await page.goto("/");
  await page.getByLabel("E-mail", { exact: true }).fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Entrar no portal" }).click();
  await expect(page.getByRole("button", { name: "Sair", exact: true })).toBeVisible();
}

async function section(page: Page, name: string) {
  await page.getByRole("navigation", { name: "Menu principal" }).getByRole("button", { name, exact: true }).click();
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  await expect(page.getByRole("status", { name: "Carregando registros" })).toHaveCount(0);
}

async function save(page: Page) {
  await page.getByRole("button", { name: "Salvar cadastro" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("status").filter({ hasText: "Cadastro realizado" })).toBeVisible();
}

test("login, dashboard, cookie protegido e logout", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("heading", { name: "Uma escola, muitas possibilidades." })).toBeVisible();
  await expect(page.getByText("Como estão suas turmas?")).toBeVisible();
  await expect(page.locator(".stat-skeleton")).toHaveCount(0);
  const cookie = (await page.context().cookies()).find(c => c.name === "siesco_session");
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe("Strict");
  await page.screenshot({ path: "test-results/dashboard-desktop.png", fullPage: true });
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Bem-vindo de volta." })).toBeVisible();
  expect((await page.request.get("/api/backend/me")).status()).toBe(401);
});

test("cadastros integrados, vínculo, atribuição e matrícula", async ({ page }) => {
  const suffix = Date.now();
  await login(page);
  const member = (await (await page.request.get("/api/backend/me")).json()).memberships[0];
  const academicPath = `/api/backend/institutions/${member.institution_id}/academic-years`;
  const years = await (await page.request.get(academicPath)).json();
  if (!years.some((year: { year: number }) => year.year === 2027)) {
    const response = await page.request.post(academicPath, { headers: { Origin: new URL(page.url()).origin }, data: { name: "2027 E2E", year: 2027, start_date: "2027-02-01", end_date: "2027-12-20" } });
    expect(response.status()).toBe(201);
  }
  await section(page, "Alunos");
  await page.getByRole("button", { name: "Cadastrar aluno", exact: true }).click();
  await page.getByLabel("Nome completo").fill(`Aluno E2E ${suffix}`);
  await page.getByLabel("Data de nascimento").fill("2015-05-10");
  await save(page);
  await expect(page.getByText(`Aluno E2E ${suffix}`, { exact: true })).toBeVisible();
  await section(page, "Responsáveis");
  await page.getByRole("button", { name: "Cadastrar responsável", exact: true }).click();
  await page.getByLabel("Nome completo").fill(`Família E2E ${suffix}`);
  await page.getByLabel("E-mail", { exact: false }).fill(`family${suffix}@example.com`);
  await save(page);
  await section(page, "Vínculos familiares");
  await page.getByRole("button", { name: "Cadastrar vínculo", exact: true }).click();
  await page.getByRole("combobox", { name: "Aluno *", exact: true }).selectOption({ label: `Aluno E2E ${suffix}` });
  await page.getByRole("combobox", { name: "Responsável *", exact: true }).selectOption({ label: `Família E2E ${suffix}` });
  await page.getByLabel("Relação com o aluno").fill("Responsável legal");
  await page.getByLabel("Vínculo pedagógico verificado pela escola").check();
  await save(page);
  await section(page, "Professores");
  await page.getByRole("button", { name: "Cadastrar professor", exact: true }).click();
  await page.getByLabel("Nome completo").fill(`Professor E2E ${suffix}`);
  await page.getByLabel("E-mail", { exact: false }).fill(`teacher${suffix}@example.com`);
  await save(page);
  await section(page, "Disciplinas");
  await page.getByRole("button", { name: "Cadastrar disciplina", exact: true }).click();
  await page.getByLabel("Nome da disciplina").fill(`Artes E2E ${suffix}`);
  await page.getByLabel("Código").fill(`ART${suffix}`);
  await save(page);
  await section(page, "Turmas");
  await page.getByRole("button", { name: "Cadastrar turma", exact: true }).click();
  await page.getByLabel("Nome da turma").fill(`Turma E2E ${suffix}`);
  await page.getByLabel("Ano letivo").fill("2027");
  await page.getByLabel("Etapa / ano escolar").fill("7º ano");
  await page.getByLabel("Turno").selectOption("morning");
  await save(page);
  await section(page, "Atribuições docentes");
  await page.getByRole("button", { name: "Cadastrar atribuição", exact: true }).click();
  await page.getByRole("combobox", { name: "Turma *", exact: true }).selectOption({ label: `Turma E2E ${suffix} · 2027` });
  await page.getByRole("combobox", { name: "Disciplina *", exact: true }).selectOption({ label: `Artes E2E ${suffix}` });
  await page.getByRole("combobox", { name: "Professor *", exact: true }).selectOption({ label: `Professor E2E ${suffix}` });
  await save(page);
  await section(page, "Matrículas");
  await page.getByRole("button", { name: "Cadastrar matrícula", exact: true }).click();
  await page.getByRole("combobox", { name: "Aluno *", exact: true }).selectOption({ label: `Aluno E2E ${suffix}` });
  await page.getByRole("combobox", { name: "Turma *", exact: true }).selectOption({ label: `Turma E2E ${suffix} · 2027` });
  await save(page);
  await expect(page.getByRole("row").filter({ hasText: `Aluno E2E ${suffix}` })).toContainText("Ativa");
  await page.getByRole("button", { name: "Cadastrar matrícula", exact: true }).click();
  await page.getByRole("combobox", { name: "Aluno *", exact: true }).selectOption({ label: `Aluno E2E ${suffix}` });
  await page.getByRole("combobox", { name: "Turma *", exact: true }).selectOption({ label: `Turma E2E ${suffix} · 2027` });
  await page.getByRole("button", { name: "Salvar cadastro" }).click();
  await expect(page.getByRole("alert")).toContainText("já possui matrícula");
});

test("perfis de família não acessam cadastros", async ({ page }) => {
  await login(page, "guardian@aurora.example.com");
  await expect(page.getByRole("heading", { name: "Vínculos escolares" })).toBeVisible();
  await expect(page.getByText("Ana Lima (fictício)", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Alunos", exact: true })).toHaveCount(0);
});

test("plataforma cadastra instituição e primeiro diretor", async ({ page }) => {
  const suffix = Date.now();
  await login(page, "admin@demo.example.com");
  await page.getByRole("button", { name: "Cadastrar instituição" }).click();
  await page.getByLabel("Nome da instituição").fill(`Escola E2E ${suffix}`);
  await page.getByLabel("Identificador").fill(`escola-${suffix}`);
  await page.getByLabel("Nome do primeiro diretor").fill("Diretor Fictício");
  await page.getByLabel("E-mail do diretor").fill(`director${suffix}@example.com`);
  await page.getByLabel("Senha inicial do diretor").fill("SenhaFicticia123!");
  await save(page);
  await expect(page.getByText(`Escola E2E ${suffix}`, { exact: true })).toBeVisible();
});

test("dashboard móvel e navegação acessível", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/dashboard-mobile.png", fullPage: true });
  await page.getByRole("button", { name: "Abrir menu", exact: true }).click();
  await section(page, "Alunos");
  await expect(page.getByRole("button", { name: "Cadastrar aluno" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("proxy bloqueia CSRF e mantém erro da API", async ({ page }) => {
  await login(page);
  const response = await page.request.post("/api/backend/auth/logout", { headers: { Origin: "https://outside.example.com" } });
  expect(response.status()).toBe(403);
  expect((await page.request.get("/api/backend/me")).status()).toBe(200);
});

test("calendário, períodos e currículo publicado vinculados à turma", async ({ page }) => {
  const suffix = Date.now();
  await login(page);
  const member = (await (await page.request.get("/api/backend/me")).json()).memberships[0];
  const years = await (await page.request.get(`/api/backend/institutions/${member.institution_id}/academic-years?limit=100`)).json();
  const year = Array.from({ length: 70 }, (_, i) => i + 2030).find(y => !years.some((row: { year: number }) => row.year === y));
  expect(year).toBeDefined();
  await section(page, "Anos letivos");
  await page.getByRole("button", { name: "Cadastrar ano letivo", exact: true }).click();
  await page.getByLabel("Nome do calendário").fill(`Calendário E2E ${suffix}`);
  await page.getByRole("spinbutton", { name: "Ano letivo *", exact: true }).fill(String(year));
  await page.getByLabel("Data inicial").fill(`${year}-02-01`);
  await page.getByLabel("Data final").fill(`${year}-12-20`);
  await save(page);

  await section(page, "Períodos letivos");
  await page.getByRole("button", { name: "Cadastrar período letivo", exact: true }).click();
  await page.getByLabel("Nome do período").fill("Primeiro bimestre");
  await page.getByRole("combobox", { name: "Calendário *", exact: true }).selectOption({ label: `Calendário E2E ${suffix}` });
  await page.getByLabel("Data inicial").fill(`${year}-02-01`);
  await page.getByLabel("Data final").fill(`${year}-04-15`);
  await save(page);
  await page.getByRole("button", { name: "Cadastrar período letivo", exact: true }).click();
  await page.getByLabel("Nome do período").fill("Segundo bimestre");
  await page.getByRole("combobox", { name: "Calendário *", exact: true }).selectOption({ label: `Calendário E2E ${suffix}` });
  await page.getByLabel("Sequência").fill("2");
  await page.getByLabel("Data inicial").fill(`${year}-04-10`);
  await page.getByLabel("Data final").fill(`${year}-06-30`);
  await page.getByRole("button", { name: "Salvar cadastro" }).click();
  await expect(page.getByRole("alert")).toContainText("sobrepõem");
  await page.getByLabel("Data inicial").fill(`${year}-04-16`);
  await save(page);

  await section(page, "Currículos");
  await page.getByRole("button", { name: "Cadastrar currículo", exact: true }).click();
  await page.getByLabel("Nome do currículo").fill(`Currículo E2E ${suffix}`);
  await page.getByLabel("Código do currículo").fill(`EF${suffix}`);
  await page.getByLabel("Etapa / ano escolar").fill("7º ano");
  await save(page);
  await section(page, "Matriz curricular");
  await page.getByRole("button", { name: "Cadastrar componente curricular", exact: true }).click();
  await page.getByRole("combobox", { name: "Currículo *", exact: true }).selectOption({ label: `Currículo E2E ${suffix} · v1` });
  await page.getByRole("combobox", { name: "Disciplina *", exact: true }).selectOption({ label: "Ciências" });
  await page.getByLabel("Carga horária").fill("120");
  await save(page);
  await section(page, "Currículos");
  const row = page.getByRole("row").filter({ hasText: `Currículo E2E ${suffix}` });
  page.once("dialog", dialog => dialog.accept());
  await row.getByRole("button", { name: "Publicar", exact: true }).click();
  await expect(row).toContainText("Publicado");
  await expect(row.getByRole("button", { name: /Editar/ })).toHaveCount(0);

  await section(page, "Turmas");
  await page.getByRole("button", { name: "Cadastrar turma", exact: true }).click();
  await page.getByLabel("Nome da turma").fill(`Turma curricular ${suffix}`);
  await page.getByLabel("Ano letivo").fill(String(year));
  await page.getByLabel("Etapa / ano escolar").fill("7º ano");
  await page.getByLabel("Currículo publicado").selectOption({ label: `Currículo E2E ${suffix} · v1` });
  await page.getByLabel("Turno").selectOption("morning");
  await save(page);
  await expect(page.getByRole("row").filter({ hasText: `Turma curricular ${suffix}` })).toContainText(`Currículo E2E ${suffix} · v1`);
  await page.screenshot({ path: "test-results/academic-classes-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.getByRole("button", { name: "Abrir menu", exact: true }).click();
  await section(page, "Anos letivos");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/academic-years-mobile.png", fullPage: true });
});
