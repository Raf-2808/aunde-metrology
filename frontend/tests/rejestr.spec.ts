import { test, expect } from "@playwright/test";

/** Loguje testowe konto z sekretem środowiska, bez utrwalania haseł w repozytorium i raporcie. */
async function zaloguj(
  page: import("@playwright/test").Page,
  rola = "administrator",
): Promise<void> {
  await page.goto("/");
  await page.getByLabel("Login", { exact: true }).fill("test-" + rola);
  await page
    .getByLabel("Hasło", { exact: true })
    .fill(process.env.TEST_LOGIN_PASSWORD!);
  await page.getByRole("button", { name: "Przejdź do ewidencji" }).click();
  await expect(
    page.getByRole("heading", { name: "Ewidencja przyrządów" }),
  ).toBeVisible();
}

test("Administrator dodaje, filtruje, edytuje i archiwizuje przyrząd", async ({
  page,
}) => {
  await zaloguj(page);
  const numer = "E2E-" + Date.now();
  await page
    .getByRole("button", { name: "+ Dodaj przyrząd", exact: true })
    .click();
  await page.getByLabel("Numer", { exact: true }).fill(numer);
  await page.getByLabel("Typ", { exact: true }).fill("Miara testowa");
  await page
    .getByLabel("Wydział bez ulicy", { exact: true })
    .fill("Cutter Wersalska");
  await page.getByRole("button", { name: "Zapisz", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const naglowek = page.getByRole("button", { name: "Numer ⌄", exact: true });
  await naglowek.click();
  await page.getByRole("button", { name: "Odznacz", exact: true }).click();
  await page.getByLabel("Szukaj wartości", { exact: true }).fill(numer);
  await page
    .getByRole("dialog", { name: "Filtr kolumny" })
    .getByLabel(numer)
    .check();
  await page.getByRole("button", { name: "Zastosuj", exact: true }).click();
  const wiersz = page
    .getByRole("row")
    .filter({ has: page.getByRole("button", { name: numer, exact: true }) });
  await expect(wiersz).toHaveCount(1);
  await expect(
    wiersz.getByRole("button", { name: "Cutter", exact: true }),
  ).toBeVisible();
  const blokada = wiersz.getByRole("cell").nth(14);
  await blokada
    .getByRole("button", { name: "Zablokowany", exact: true })
    .click();
  await page
    .getByLabel("Edytuj dopuszczenie", { exact: true })
    .selectOption("true");
  await page.getByLabel("Edytuj dopuszczenie", { exact: true }).press("Enter");
  await expect(blokada).toHaveText("Odblokowany");
  await wiersz.getByRole("cell").nth(12).getByRole("button").click();
  await page
    .getByLabel("Edytuj stan_techniczny", { exact: true })
    .selectOption("Niesprawny");
  await page
    .getByLabel("Edytuj stan_techniczny", { exact: true })
    .press("Enter");
  await expect(blokada).toHaveText("Zablokowany");
  await wiersz.getByRole("cell").nth(12).getByRole("button").click();
  await page
    .getByLabel("Edytuj stan_techniczny", { exact: true })
    .selectOption("Sprawny");
  await page
    .getByLabel("Edytuj stan_techniczny", { exact: true })
    .press("Enter");
  await expect(blokada).toHaveText("Odblokowany");
  await blokada
    .getByRole("button", { name: "Odblokowany", exact: true })
    .click();
  await page
    .getByLabel("Edytuj dopuszczenie", { exact: true })
    .selectOption("false");
  await page.getByLabel("Edytuj dopuszczenie", { exact: true }).press("Enter");
  await expect(blokada).toHaveText("Zablokowany");
  await wiersz.getByRole("button", { name: "Cutter", exact: true }).click();
  const pole = page.getByLabel("Edytuj wydzial", { exact: true });
  await pole.fill("Magazyn Senatorska");
  await pole.press("Enter");
  await expect(
    wiersz.getByRole("button", { name: "Magazyn", exact: true }),
  ).toBeVisible();
  await wiersz.getByRole("cell").nth(8).getByRole("button").click();
  await page.getByLabel("Edytuj ostatni", { exact: true }).fill("2026-01-31");
  await page.getByLabel("Edytuj ostatni", { exact: true }).press("Enter");
  await expect(wiersz.getByRole("cell").nth(8)).toHaveText("2026-01-31");
  await wiersz.getByRole("cell").nth(9).getByRole("button").click();
  await page.getByLabel("Edytuj interwal", { exact: true }).fill("1");
  await page.getByLabel("Edytuj interwal", { exact: true }).press("Enter");
  await expect(wiersz.getByRole("cell").nth(10)).toHaveText("2026-02-28");
  if (process.env.TEST_SCREEN_DIR)
    await page.screenshot({
      path: process.env.TEST_SCREEN_DIR + "/aunde_metrologia_rejestr.png",
      fullPage: true,
    });
  await wiersz.getByRole("button", { name: "Usuń", exact: true }).click();
  await page.getByRole("button", { name: "Potwierdź", exact: true }).click();
  await expect(wiersz).toHaveCount(0);
  await page.getByLabel("Archiwum", { exact: true }).check();
  await expect(
    page.getByRole("heading", { name: "Archiwum przyrządów" }),
  ).toBeVisible();
  await expect(wiersz).toHaveCount(1);
  await wiersz.getByRole("button", { name: "Przywróć", exact: true }).click();
  await page.getByRole("button", { name: "Potwierdź", exact: true }).click();
  await expect(wiersz).toHaveCount(0);
});

test("Viewer nie otrzymuje R&R i nie ma edycji", async ({ page }) => {
  await zaloguj(page, "viewer");
  await expect(
    page.getByRole("button", { name: "R&R ⌄", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "+ Dodaj przyrząd", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Zapisz czynność" }),
  ).toHaveCount(0);
});

test("Administrator zarządza kontami bez ujawniania haseł", async ({
  page,
}) => {
  await zaloguj(page);
  await page
    .getByRole("button", { name: "Zarządzaj kontami", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Zarządzanie kontami" });
  const login = "e2e-konto-" + Date.now();
  await dialog.getByLabel("Login", { exact: true }).fill(login);
  await dialog
    .getByLabel("Nowe hasło", { exact: true })
    .fill("syntetyczne-haslo-123");
  await dialog
    .getByRole("button", { name: "Zapisz konto", exact: true })
    .click();
  const wpis = dialog.locator(".wpis").filter({ hasText: login });
  await expect(wpis).toBeVisible();
  await wpis.getByRole("combobox").selectOption("Editor");
  await expect(wpis.getByRole("combobox")).toHaveValue("Editor");
  await wpis.getByRole("button", { name: "Dezaktywuj", exact: true }).click();
  await expect(
    wpis.getByRole("button", { name: "Aktywuj", exact: true }),
  ).toBeVisible();
});

test("Publiczny QR rejestruje otwarcie i ponowne wejście bez R&R", async ({
  page,
  request,
}) => {
  const token = process.env.TEST_QR_TOKEN!;
  let odczyty = 0;
  page.on("response", (odp) => {
    if (odp.url().includes("/public/otwarcie/") && odp.ok()) odczyty++;
  });
  await page.goto("/p/" + token);
  await expect(
    page.getByText("DOPUSZCZENIE DO UŻYTKOWANIA", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Historia odczytów QR" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  if (process.env.TEST_SCREEN_DIR)
    await page.screenshot({
      path: process.env.TEST_SCREEN_DIR + "/aunde_metrologia_karta_qr.png",
      fullPage: true,
    });
  await expect(page.locator("dt").filter({ hasText: "R&R" })).toHaveCount(0);
  await expect.poll(() => odczyty).toBe(1);
  await page.reload();
  await expect.poll(() => odczyty).toBe(2);
  const odp = await request.post("/public/otwarcie/" + token, {
    data: { zdarzenie: crypto.randomUUID() },
  });
  expect(odp.ok()).toBeTruthy();
  expect(Object.keys((await odp.json()).przyrzad)).not.toContain("rr");
  expect(
    (
      await request.patch("/public/przyrzady/test", {
        data: { status: "Aktywna" },
      })
    ).status(),
  ).toBe(404);
});
