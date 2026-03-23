import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  const page = await context.newPage();
  
  await page.goto('http://localhost:5173/chat');
  await page.waitForTimeout(2000);
  
  await page.screenshot({ path: 'screenshot.png' });
  
  await browser.close();
})();
