import { chromium, expect } from '@playwright/test';

(async () => {
  console.log("Starting UI Verification...");
  
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream' // Provides a fake video/audio feed
    ]
  });
  
  const context = await browser.newContext({
    permissions: ['camera', 'microphone']
  });
  
  const page = await context.newPage();
  
  try {
    console.log("1. Navigating to the app...");
    await page.goto('http://localhost:5173/');
    
    // Check initial layout
    await page.waitForSelector('header');
    console.log("Header loaded.");

    // Task: Verify the video preview displays exactly as requested when the camera is toggled.
    console.log("2. Checking Video Preview...");
    // Find the camera toggle button. Based on typical UI, it might be in the header or main view.
    // Let's dump some text to understand the layout
    const text = await page.evaluate(() => document.body.innerText);
    console.log("Page text:", text.slice(0, 200).replace(/\n/g, ' '));
    
    const videos = await page.locator('video').count();
    console.log(`Initial video elements count: ${videos}`);
    
    // Keep it open for a sec to let react render
    await page.waitForTimeout(2000);

    const videoElements = await page.locator('video').all();
    if (videoElements.length > 0) {
      console.log("Video preview found.");
      const box = await videoElements[0].boundingBox();
      console.log("Video bounding box:", box);
    } else {
      console.log("No video element found. Looking for camera toggle...");
      // Let's click the camera toggle button
      // To find the button, we can look for specific text or aria labels
      // "开启摄像头" / "关闭摄像头"
      const buttons = await page.locator('button').allInnerTexts();
      console.log("Available buttons:", buttons);
    }
    
    // Task: Test "Voice Mode" thoroughly
    console.log("3. Testing Voice Mode...");
    // Typically there's a voice mode button
    
    // Check chat interface
    console.log("4. Checking Chat Loop components...");
    
    // Wait for the UI tests to print
  } catch (error) {
    console.error("Test failed:", error);
  } finally {
    await browser.close();
  }
})();
