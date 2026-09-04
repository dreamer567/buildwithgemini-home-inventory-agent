#!/usr/bin/env node
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

function addGlobalModulePath() {
  try {
    const globalRoot = execSync('npm root -g', { encoding: 'utf8' }).trim();
    if (globalRoot && fs.existsSync(globalRoot) && !module.paths.includes(globalRoot)) {
      module.paths.unshift(globalRoot);
    }
    return !!globalRoot;
  } catch (e) {
    return false;
  }
}

addGlobalModulePath();
const { chromium } = require('playwright');

function hasFfmpeg() {
  try {
    execSync('ffmpeg -version', { stdio: 'ignore' });
    return true;
  } catch (e) {
    return false;
  }
}

function probeDuration(file) {
  try {
    const out = execSync(
      `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${file}"`,
      { encoding: 'utf8' }
    ).trim();
    const d = parseFloat(out);
    return Number.isFinite(d) ? d : null;
  } catch (e) {
    return null;
  }
}

const LYRIA_MODEL = 'lyria-002';
const LYRIA_REGION = 'us-central1';

function gcloudValue(cmd) {
  return execSync(cmd, { encoding: 'utf8' }).trim();
}

function resolveGcpProject() {
  return (
    process.env.GOOGLE_CLOUD_PROJECT ||
    process.env.GOOGLE_CLOUD_QUOTA_PROJECT ||
    gcloudValue('gcloud config get-value project')
  );
}

async function generateMusic({ prompt, negativePrompt }) {
  const project = resolveGcpProject();
  if (!project) throw new Error('No GCP project found.');
  const token = gcloudValue('gcloud auth print-access-token');
  if (!token) throw new Error('No access token.');

  const url = `https://${LYRIA_REGION}-aiplatform.googleapis.com/v1/projects/${project}/locations/${LYRIA_REGION}/publishers/google/models/${LYRIA_MODEL}:predict`;
  const instance = { prompt };
  if (negativePrompt) instance.negative_prompt = negativePrompt;
  const body = { instances: [instance], parameters: { sample_count: 1 } };

  const res = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Lyria API error: ${res.status} ${text.slice(0, 300)}`);
  }
  const json = await res.json();
  const pred = json.predictions && json.predictions[0];
  const b64 = pred && (pred.bytesBase64Encoded || pred.audioContent);
  if (!b64) throw new Error('No audio bytes in Lyria response.');
  return Buffer.from(b64, 'base64');
}

function muxMusicIntoVideo({ videoPath, wavPath, outPath, volume }) {
  const dur = probeDuration(videoPath);
  if (!dur) throw new Error('Could not probe video duration.');
  const fadeIn = Math.min(1.0, dur / 4);
  const fadeOutDur = Math.min(2.0, dur / 3);
  const fadeOutStart = Math.max(0, dur - fadeOutDur);
  const af = `afade=t=in:st=0:d=${fadeIn.toFixed(2)},afade=t=out:st=${fadeOutStart.toFixed(2)}:d=${fadeOutDur.toFixed(2)},volume=${volume}`;
  execSync(
    `ffmpeg -y -i "${videoPath}" -stream_loop -1 -i "${wavPath}" ` +
      `-filter:a "${af}" -map 0:v:0 -map 1:a:0 -t ${dur.toFixed(3)} ` +
      `-c:v copy -c:a libopus -b:a 128k -shortest "${outPath}"`,
    { stdio: 'ignore' }
  );
}

function loadFrameAssets() {
  const css = `
    #gwt-frame {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      pointer-events: none;
      z-index: 999999;
      box-sizing: border-box;
      border: 3px solid rgba(255, 255, 255, 0.18);
    }
    #gwt-badge {
      position: absolute;
      top: 12px;
      right: 18px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 9999px;
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      font-size: 13px;
      font-weight: 500;
      box-shadow: 0 4px 16px rgba(0,0,0,0.4);
    }
  `;
  const logo = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#38bdf8" stroke-width="2" stroke-linejoin="round"/>
      <path d="M2 17L12 22L22 17" stroke="#38bdf8" stroke-width="2" stroke-linejoin="round"/>
      <path d="M2 12L12 17L22 12" stroke="#38bdf8" stroke-width="2" stroke-linejoin="round"/>
    </svg>
  `;
  return { css, logo };
}

async function injectFrame(page, { title, assets }) {
  try {
    await page.evaluate(({ title, css, logo }) => {
      if (!document.getElementById('gwt-frame-style')) {
        const style = document.createElement('style');
        style.id = 'gwt-frame-style';
        style.textContent = css;
        (document.head || document.documentElement).appendChild(style);
      }
      if (!document.getElementById('gwt-frame')) {
        const frame = document.createElement('div');
        frame.id = 'gwt-frame';
        const badge = document.createElement('div');
        badge.id = 'gwt-badge';
        badge.innerHTML = logo;
        const label = document.createElement('span');
        label.textContent = title;
        badge.appendChild(label);
        frame.appendChild(badge);
        document.documentElement.appendChild(frame);
      }
    }, { title, css: assets.css, logo: assets.logo });
  } catch (e) {}
}

(async () => {
  const targetUrl = 'http://localhost:8080/?lang=zh';
  const outputPath = path.resolve(__dirname, 'assets', 'agent_demo.webm');
  const title = '3LDK 三口之家物品收纳与生活采购智能管家 (中文版)';
  const musicPrompt = 'peaceful cozy lo-fi chill hip-hop, gentle acoustic piano, soft vinyl crackle, warm home atmosphere beats';
  const speed = 1.5;
  const viewport = { width: 1280, height: 800 };

  const tempDir = path.join(process.cwd(), '.video_tmp_zh');
  if (fs.existsSync(tempDir)) fs.rmSync(tempDir, { recursive: true, force: true });
  fs.mkdirSync(tempDir, { recursive: true });

  console.log('--- Chinese Rich Demo Recorder ---');
  console.log(`URL: ${targetUrl}`);
  console.log(`Output: ${outputPath}`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport,
    recordVideo: { dir: tempDir, size: viewport },
  });

  const page = await context.newPage();
  const assets = loadFrameAssets();

  console.log('Navigating to UI...');
  await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 30000 });
  page.on('framenavigated', () => injectFrame(page, { title, assets }));
  await injectFrame(page, { title, assets });
  await page.waitForTimeout(2000);

  async function waitForReplyCompletion(timeout = 55000) {
    try {
      await page.waitForSelector('.typing-indicator', { state: 'attached', timeout: 3500 });
    } catch (e) {}
    await page.waitForSelector('.typing-indicator', { state: 'detached', timeout });
    await page.waitForTimeout(2500);
  }

  // 1. Showcase 3D floorplan
  console.log('[Action 1] Interacting with 3D Isometric Floorplan...');
  await page.hover('#iso-room-bed1');
  await page.waitForTimeout(800);
  await page.hover('#iso-room-ldk');
  await page.waitForTimeout(700);
  console.log('Clicking 3D LDK Room...');
  await page.click('#iso-room-ldk');
  await injectFrame(page, { title, assets });
  console.log('Waiting for LDK room items & freshness status...');
  await waitForReplyCompletion();

  // 2. Click Quick Suggestion Prompt Button
  console.log('[Action 2] Clicking Quick Prompt: 检查库存并生成家庭采购清单...');
  const promptButtons = page.locator('.prompt-pill');
  if (await promptButtons.count() >= 2) {
    await promptButtons.nth(1).hover();
    await page.waitForTimeout(600);
    await promptButtons.nth(1).click();
  } else {
    await page.click('#input');
    await page.fill('#input', '检查冰箱与家庭备货库存，生成一份优先级清晰的生活采购清单');
    await page.press('#input', 'Enter');
  }
  await injectFrame(page, { title, assets });
  console.log('Waiting for shopping checklist...');
  await waitForReplyCompletion();

  // 3. Interact with shopping checklist checkboxes
  console.log('[Action 3] Interacting with Checklist Checkboxes...');
  const checklistCards = page.locator('.checklist-card');
  const checkCount = await checklistCards.count();
  if (checkCount > 0) {
    await checklistCards.nth(0).hover();
    await page.waitForTimeout(600);
    await checklistCards.nth(0).click();
    console.log('Checked item 1!');
    await page.waitForTimeout(800);
    if (checkCount > 1) {
      await checklistCards.nth(1).hover();
      await page.waitForTimeout(600);
      await checklistCards.nth(1).click();
      console.log('Checked item 2!');
      await page.waitForTimeout(800);
    }
  }

  // 4. Type direct Chinese query
  console.log('[Action 4] Typing direct Chinese query...');
  const inputElem = page.locator('#input');
  await inputElem.click();
  await page.waitForTimeout(600);
  await inputElem.pressSequentially('家里的剪刀都放在哪里了？', { delay: 60 });
  await page.waitForTimeout(800);
  await inputElem.press('Enter');
  await injectFrame(page, { title, assets });
  console.log('Waiting for scissors response...');
  await waitForReplyCompletion();
  await page.waitForTimeout(4000);

  console.log('Closing browser and finalizing video...');
  await page.close();
  await context.close();
  await browser.close();

  const videoFiles = fs.readdirSync(tempDir).filter(f => f.endsWith('.webm'));
  if (videoFiles.length === 0) throw new Error('No recording file found.');
  const rawVideo = path.join(tempDir, videoFiles[0]);

  let currentVideo = rawVideo;
  if (speed !== 1.0 && hasFfmpeg()) {
    console.log(`Speeding up video by ${speed}x...`);
    const spedUp = path.join(tempDir, 'sped_up.webm');
    execSync(
      `ffmpeg -y -i "${currentVideo}" -filter:v "setpts=PTS/${speed}" -an "${spedUp}"`,
      { stdio: 'ignore' }
    );
    currentVideo = spedUp;
  }

  if (hasFfmpeg()) {
    try {
      console.log(`Generating Chinese lo-fi music with Lyria (${LYRIA_MODEL})...`);
      const wavBytes = await generateMusic({ prompt: musicPrompt });
      const wavPath = path.join(tempDir, 'lyria.wav');
      fs.writeFileSync(wavPath, wavBytes);
      console.log('Muxing music into video...');
      muxMusicIntoVideo({
        videoPath: currentVideo,
        wavPath,
        outPath: outputPath,
        volume: 0.5,
      });
      console.log(`SUCCESS: Saved Chinese demo to ${outputPath}`);
    } catch (err) {
      console.warn(`Music failed: ${err.message}. Copying video without music.`);
      fs.copyFileSync(currentVideo, outputPath);
    }

    // Convert to GIF for README display
    try {
      console.log('Generating high-quality GIF preview for README...');
      const gifPath = path.resolve(__dirname, 'assets', 'demo.gif');
      execSync(
        `ffmpeg -y -i "${outputPath}" -vf "fps=10,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer" "${gifPath}"`,
        { stdio: 'ignore' }
      );
      fs.copyFileSync(gifPath, path.resolve(__dirname, 'demo.gif'));
      fs.copyFileSync(outputPath, path.resolve(__dirname, 'agent_demo.webm'));
      console.log(`SUCCESS: Saved demo.gif to ${gifPath}`);
    } catch (e) {
      console.warn(`GIF generation failed: ${e.message}`);
    }
  } else {
    fs.copyFileSync(currentVideo, outputPath);
  }

  fs.rmSync(tempDir, { recursive: true, force: true });
  console.log('Done!');
})();
