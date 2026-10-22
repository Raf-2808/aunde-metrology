import {test,expect} from '@playwright/test';
test('logowanie nie ujawnia chronionych wyników',async({page})=>{await page.goto('/');await expect(page.getByRole('heading',{name:'Laboratorium pod kontrolą.'})).toBeVisible();await expect(page.getByRole('button',{name:'Zaloguj się →'})).toBeVisible();await expect(page.getByRole('table')).toHaveCount(0);});
