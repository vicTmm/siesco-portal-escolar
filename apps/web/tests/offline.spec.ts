import { test, expect } from "@playwright/test";
test("diário preparado funciona sem rede e sincroniza ao reconectar", async ({
  page,
  context,
}) => {
  const password = process.env.DEMO_PASSWORD!;
  await page.goto("/");
  await page
    .getByLabel("E-mail", { exact: true })
    .fill("director@aurora.example.com");
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar no portal" }).click();
  await expect(
    page.getByRole("button", { name: "Sair", exact: true }),
  ).toBeVisible();
  const origin = new URL(page.url()).origin,
    me = await (await page.request.get("/api/backend/me")).json(),
    base = "/api/backend/institutions/" + me.memberships[0].institution_id;
  const get = async (p: string) =>
    (await page.request.get(base + "/" + p)).json();
  const post = async (p: string, data: unknown) => {
    const r = await page.request.post(base + "/" + p, {
      headers: { Origin: origin },
      data,
    });
    expect(r.status(), await r.text()).toBe(201);
    return r.json();
  };
  const suffix = Date.now(),
    years = await get("academic-years?limit=100"),
    year = Array.from({ length: 65 }, (_, i) => 2030 + i).find(
      (y) => !years.some((r: { year: number }) => r.year === y),
    )!;
  const calendar = await post("academic-years", {
    name: "Offline " + suffix,
    year,
    start_date: `${year}-02-01`,
    end_date: `${year}-12-20`,
  });
  const term = await post("academic-terms", {
    name: "Período offline " + suffix,
    academic_year_id: calendar.id,
    sequence: 1,
    start_date: `${year}-02-01`,
    end_date: `${year}-12-20`,
  });
  const group = await post("classes", {
    name: "Turma offline " + suffix,
    academic_year: year,
    grade_level: "6º ano",
    shift: "morning",
    capacity: 30,
  });
  const teacher = (await get("teachers"))[0],
    subject = (await get("subjects"))[0];
  const assignment = await post("assignments", {
    class_id: group.id,
    teacher_id: teacher.id,
    subject_id: subject.id,
  });
  const student = await post("students", {
    name: "Aluno offline " + suffix,
    birth_date: "2015-03-10",
  });
  await post("enrollments", { student_id: student.id, class_id: group.id });
  const policy = await post("grading-policies", {
    name: "Regra offline " + suffix,
    method: "simple",
    scale: 10,
    passing: 6,
    attendance_min: 75,
    decimals: 1,
    recovery: "none",
  });
  const journal = await post("journals", {
    assignment_id: assignment.id,
    term_id: term.id,
    policy_id: policy.id,
  });
  await page.goto("/offline");
  await expect(
    page.getByRole("heading", { name: "Diário offline", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: new RegExp(group.name) }).click();
  await expect(page.getByRole("status")).toContainText("Diário preparado");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await expect
    .poll(() =>
      page.evaluate(() => Boolean(navigator.serviceWorker.controller)),
    )
    .toBe(true);
  await context.setOffline(true);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Diário offline", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Diário preparado", { exact: true })
    .selectOption(me.memberships[0].id + "/" + journal.id);
  await page.getByLabel("Data", { exact: true }).fill(`${year}-03-03`);
  await page
    .getByLabel("Conteúdo / plano de aula", { exact: true })
    .fill("Plano e chamada guardados sem internet");
  await page.getByLabel(student.name, { exact: true }).selectOption("present");
  await page
    .getByRole("button", { name: "Guardar rascunho local", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Rascunho guardado");
  await context.setOffline(false);
  await expect(page.getByRole("status")).toContainText(
    "Rascunhos sincronizados",
  );
  const detail = await get("journals/" + journal.id);
  expect(detail.lessons).toHaveLength(1);
  expect(detail.lessons[0].attendance[0].status).toBe("present");
  // Another staff member changes the diary while this device has a local draft.
  await context.setOffline(true);
  await page.getByLabel("Data", { exact: true }).fill(`${year}-03-04`);
  await page.getByLabel("Conteúdo / plano de aula", { exact: true }).fill("Rascunho a revisar");
  await page.getByLabel(student.name, { exact: true }).selectOption("present");
  await page.getByRole("button", { name: "Guardar rascunho local", exact: true }).click();
  await post(`journals/${journal.id}/lessons`, { version: detail.version, date: `${year}-03-05`, slot: 1, content: "Aula registrada em outro dispositivo" });
  await context.setOffline(false);
  await expect(page.getByRole("alert").filter({ hasText: "rascunhos continuam" })).toBeVisible();
  await page.getByRole("button", { name: "Revisar versão atual e conflitos" }).click();
  await page.getByLabel(/Reaplicar aula/).check();
  await page.getByLabel("Revisei as diferenças e confirmo a seleção.").check();
  await page.getByRole("button", { name: "Concluir revisão e sincronizar seleção" }).click();
  await expect(page.getByText("Histórico local de revisão (1)")).toBeVisible();
  await expect.poll(async () => (await get(`journals/${journal.id}`)).lessons.length).toBe(3);
  // Expired authentication preserves pending work until the same user logs in.
  await context.setOffline(true);
  await page.getByLabel("Data", { exact: true }).fill(`${year}-03-06`);
  await page.getByLabel("Conteúdo / plano de aula", { exact: true }).fill("Rascunho preservado após expiração");
  await page.getByLabel(student.name, { exact: true }).selectOption("present");
  await page.getByRole("button", { name: "Guardar rascunho local", exact: true }).click();
  await context.clearCookies();
  await context.setOffline(false);
  await expect(page.getByRole("heading", { name: "Revalidar acesso ao diário offline" })).toBeVisible();
  await expect(page.getByText(/Seus rascunhos foram preservados/)).toBeVisible();
  await page.getByRole("link", { name: "Entrar no portal" }).click();
  await page.getByLabel("E-mail", { exact: true }).fill("director@aurora.example.com");
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar no portal" }).click();
  await expect(page.getByRole("button", { name: "Sair", exact: true })).toBeVisible();
  await page.goto("/offline");
  await expect(page.getByRole("status")).toContainText("Rascunhos sincronizados");
  expect((await get(`journals/${journal.id}`)).lessons).toHaveLength(4);
  await page.goto("/");
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page.getByLabel("E-mail", { exact: true })).toBeVisible();
  await page.goto("/offline");
  await expect(
    page.getByText(/Nenhum diário preparado\./),
  ).toBeVisible();
});
