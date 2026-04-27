import fs from 'fs';
import path from 'path';
import { workflow, type LibrettoWorkflowContext } from '@balaji-g42/libretto';

const LOGIN_URL  = 'https://app.drchrono.com/accounts/login/';
const BASE_URL   = 'https://lxavier.drchrono.com';
const OUTPUT_DIR = path.join(process.cwd(), 'output', 'drchrono');

const USERNAME = process.env.drchrono_username ?? '';
const PASSWORD = process.env.drchrono_password ?? '';
const API_BASE = (process.env.API_BASE_URL ?? '').replace(/\/$/, '');
const API_KEY  = process.env.API_KEY ?? '';

if (!USERNAME || !PASSWORD) throw new Error('drchrono_username and drchrono_password must be set in .env');
if (!API_BASE || !API_KEY)  throw new Error('API_BASE_URL and API_KEY must be set in .env');

const API_HEADERS: Record<string, string> = { 'X-Api-Key': API_KEY };

type Output = { advancedReportName: string; downloadedFiles: string[] };

function todayMMDDYYYY(): string {
  const d = new Date();
  return `${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getDate()).padStart(2,'0')}/${d.getFullYear()}`;
}

function dateOffsetMMDDYYYY(yearsAgo: number): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - yearsAgo);
  return `${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getDate()).padStart(2,'0')}/${d.getFullYear()}`;
}

function buildReportName(): string {
  const d = new Date();
  return `HBox-EMR-${String(d.getDate()).padStart(2,'0')}-${String(d.getMonth()+1).padStart(2,'0')}-${d.getFullYear()}`;
}

async function consolidateViaAPI(outputDir: string, reportName: string, session: string): Promise<string | null> {
  const allCsvs  = fs.readdirSync(outputDir).filter((f: string) => f.endsWith('.csv'));
  const medFile  = allCsvs.find((f: string) => f.startsWith('medication_report_'));
  const probFile = allCsvs.find((f: string) => f.startsWith('problem_report_'));
  const emrFile  = allCsvs.find((f: string) => f !== medFile && f !== probFile);

  console.log(`[${session}] Uploading to XHI API:`);
  console.log(`[${session}]   EMR report     : ${emrFile  ?? '⚠ NOT FOUND'}`);
  console.log(`[${session}]   Medication     : ${medFile  ?? '⚠ NOT FOUND'}`);
  console.log(`[${session}]   Problem list   : ${probFile ?? '⚠ NOT FOUND'}`);

  if (!medFile || !probFile || !emrFile) {
    console.warn(`[${session}] ⚠ Missing one or more CSV files — skipping consolidation`);
    return null;
  }

  // POST /api/xhi/process
  const form = new FormData();
  form.append('emr_report',        new Blob([fs.readFileSync(path.join(outputDir, emrFile))],  { type: 'text/csv' }), emrFile);
  form.append('medication_report', new Blob([fs.readFileSync(path.join(outputDir, medFile))],  { type: 'text/csv' }), medFile);
  form.append('problem_report',    new Blob([fs.readFileSync(path.join(outputDir, probFile))], { type: 'text/csv' }), probFile);

  const submitRes = await fetch(`${API_BASE}/api/xhi/process`, { method: 'POST', headers: { 'X-Api-Key': API_KEY }, body: form });
  if (!submitRes.ok) {
    const raw = await submitRes.text();
    let detail = raw;
    try {
      const parsed = JSON.parse(raw);
      detail = parsed.traceback ?? parsed.detail ?? raw;
    } catch {}
    throw new Error(`XHI submit failed ${submitRes.status}:\n${detail}`);
  }
  const { job_id } = await submitRes.json() as { job_id: string };
  console.log(`[${session}] Job created      — job_id: ${job_id}`);

  // Poll /api/xhi/jobs/{job_id}
  const DEADLINE_MS = Date.now() + 30 * 60_000;
  let status = '';
  while (Date.now() < DEADLINE_MS) {
    await new Promise(r => setTimeout(r, 15_000));
    const pollRes = await fetch(`${API_BASE}/api/xhi/jobs/${job_id}`, { headers: API_HEADERS });
    if (!pollRes.ok) throw new Error(`XHI poll failed ${pollRes.status}`);
    const job = await pollRes.json() as { status: string; error?: string; log?: string };
    status = job.status;
    if (status === 'running' || status === 'pending') {
      console.log(`[${session}] Job running      — ${job_id} [${status}]`);
    } else if (status === 'done') {
      console.log(`[${session}] Job completed    — ${job_id}`);
      break;
    } else if (status === 'failed' || status === 'error') {
      const logText = job.log ? `\n\nPipeline log:\n${job.log}` : '';
      throw new Error(`XHI pipeline failed: ${job.error ?? status}${logText}`);
    } else {
      console.log(`[${session}] Job status       — ${job_id} [${status}]`);
    }
  }
  if (status !== 'done') throw new Error('XHI job timed out after 30 min');

  // GET /api/xhi/jobs/{job_id}/download
  console.log(`[${session}] Downloading consolidated file...`);
  const dlRes = await fetch(`${API_BASE}/api/xhi/jobs/${job_id}/download`, { headers: API_HEADERS });
  if (!dlRes.ok) throw new Error(`XHI download failed ${dlRes.status}`);
  const disposition = dlRes.headers.get('content-disposition') ?? '';
  const fnMatch = disposition.match(/filename="([^"]+)"/);
  const outName = fnMatch ? fnMatch[1] : `XHI_consolidated_${reportName}.xlsx`;
  const outPath = path.join(outputDir, outName);
  fs.writeFileSync(outPath, new Uint8Array(await dlRes.arrayBuffer()));
  console.log(`[${session}] Consolidated file : ${outName}`);
  return outName;
}

export default workflow<void, Output>(
  'drchrono-submit',
  async ({ session, page }: LibrettoWorkflowContext): Promise<Output> => {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    const downloadedFiles: string[] = [];
    const today = todayMMDDYYYY();
    const name  = buildReportName();

    await page.route(
      /heapanalytics\.com|fullstory\.com|segment\.io|cdn\.segment\.com|nr-data\.net|newrelic\.com|chameleon\.io|intercom\.io|sentry\.drchrono\.dev/,
      (route: any) => route.abort(),
    );

    // ── 1. LOGIN ──────────────────────────────────────────────────────────────
    console.log(`[${session}] Logging in to DrChrono`);
    await page.goto(LOGIN_URL, { waitUntil: 'domcontentloaded' });
    await page.locator('#username').fill(USERNAME);
    await page.locator('#username').press('Enter');
    await page.waitForSelector('#password', { timeout: 10_000 });
    await page.locator('#password').fill(PASSWORD);
    await page.locator('#password').press('Enter');
    await page.waitForFunction(() => !window.location.href.includes('/accounts/login'), { timeout: 30_000 });
    console.log(`[${session}] Logged in — ${page.url()}`);
    await page.goto('about:blank', { waitUntil: 'domcontentloaded' });

    // ── 2. ADVANCED REPORT — queue async export ───────────────────────────────
    console.log(`[${session}] Submitting Advanced Report export: ${name}`);
    const advExportUrl = `${BASE_URL}/analytics/advanced_report/export_custom?` + [
      `_export_report_name=${encodeURIComponent(name)}`,
      '_page=1', '_results_per_page=50',
      'a_icd=true', 'a_notes=true', 'a_provider=true', 'a_reason=true',
      `appt_created_at_end=${encodeURIComponent(today)}`,
      'appt_created_at_start=01%2F01%2F2025',
      'd_organization_name=true', 'd_prescribing_physician_name=true',
      'display_type=C', 'filter_archived_exam_rooms=', 'filter_breaks=', 'filter_by_patient_only=',
      'p_address=true', 'p_cell_phone=true', 'p_chart=true', 'p_city=true', 'p_copay=true',
      'p_dob=true', 'p_doctor=true', 'p_dos_last=true', 'p_dos_next=true', 'p_email=true',
      'p_emerg_contact_name=true', 'p_emerg_contact_phone=true', 'p_emerg_contact_relation=true',
      'p_firstname=true', 'p_fullname=true', 'p_gender=true', 'p_home_phone=true',
      'p_ins1_group_num=true', 'p_ins1_id_num=true', 'p_ins1_name=true',
      'p_ins2_group_num=true', 'p_ins2_id_num=true', 'p_ins2_name=true',
      'p_lastname=true', 'p_office_phone=true', 'p_primary_care_physician=true',
      'p_race=true', 'p_ref_dr=true', 'p_state=true', 'p_zip_code=true',
      'patient_default_appointment_profile=', 'patient_doctor=', 'patient_status=A',
    ].join('&');

    const advR = await page.context().request.get(advExportUrl, { timeout: 30_000 });
    console.log(`[${session}] Advanced report queued — status ${advR.status()}: ${(await advR.text()).slice(0, 100)}`);

    // ── 3. MEDICATION REPORT — 1-year range ──────────────────────────────────
    console.log(`[${session}] Fetching Medication Report CSV`);
    const medR       = await page.context().request.get(`${BASE_URL}/analytics/medication_report/export_csv?page=1&prescribed_start=${encodeURIComponent(dateOffsetMMDDYYYY(1))}&prescribed_end=${encodeURIComponent(today)}`, { timeout: 30_000 });
    const medCsvText = await medR.text();
    const medFilename = `medication_report_${name}.csv`;
    const medFilePath = path.join(OUTPUT_DIR, medFilename);
    fs.writeFileSync(medFilePath, medCsvText);
    downloadedFiles.push(medFilePath);
    console.log(`[${session}] Downloaded        : ${medFilename} (${medCsvText.length.toLocaleString()} bytes)`);

    // ── 4. PROBLEM REPORT — 5-year range ─────────────────────────────────────
    console.log(`[${session}] Fetching Problem Report CSV`);
    const probR       = await page.context().request.get(`${BASE_URL}/analytics/problem_report/export_csv?page=1&start_date=${encodeURIComponent(dateOffsetMMDDYYYY(5))}&end_date=${encodeURIComponent(today)}`, { timeout: 30_000 });
    const probCsvText = await probR.text();
    const probFilename = `problem_report_${name}.csv`;
    const probFilePath = path.join(OUTPUT_DIR, probFilename);
    fs.writeFileSync(probFilePath, probCsvText);
    downloadedFiles.push(probFilePath);
    console.log(`[${session}] Downloaded        : ${probFilename} (${probCsvText.length.toLocaleString()} bytes)`);

    // ── 5. POLL FOR ADVANCED REPORT ZIP ──────────────────────────────────────
    console.log(`[${session}] Waiting 2 min for advanced report to generate...`);
    await page.goto('about:blank', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(120_000);

    let advancedReportDownloaded = false;
    for (let attempt = 1; attempt <= 5 && !advancedReportDownloaded; attempt++) {
      console.log(`[${session}] Messages check attempt ${attempt}/5`);
      const resp = await page.context().request.get(`${BASE_URL}/messages/`, { timeout: 15_000 }).catch(() => null);
      const html = resp ? await resp.text().catch(() => '') : '';

      if (html.includes(name)) {
        const s3Match = html.match(/https:\/\/[^"'\s<>]+s3[^"'\s<>]*amazonaws[^"'\s<>]+/);
        const s3Url = s3Match ? s3Match[0].replace(/&amp;/g, '&') : null;
        if (s3Url) {
          console.log(`[${session}] S3 URL found — downloading ZIP...`);
          const s3Resp = await page.context().request.get(s3Url, { timeout: 60_000 });
          const zipBody = await s3Resp.body();
          if (!zipBody || zipBody.length < 100) {
            console.warn(`[${session}] ⚠ S3 response too small (${zipBody?.length ?? 0} bytes) — ZIP not ready, retrying`);
          } else {
            const zipFilename = `${name}.zip`;
            const advFile = path.join(OUTPUT_DIR, zipFilename);
            fs.writeFileSync(advFile, zipBody);
            console.log(`[${session}] Downloaded        : ${zipFilename} (${zipBody.length.toLocaleString()} bytes)`);

            const { execSync } = await import('child_process');
            const beforeFiles = new Set(fs.readdirSync(OUTPUT_DIR));
            try {
              execSync(`powershell -Command "Expand-Archive -Path '${advFile}' -DestinationPath '${OUTPUT_DIR}' -Force"`, { stdio: 'pipe' });
            } catch (err: any) {
              console.error(`[${session}] ✖ Expand-Archive error: ${err.stderr?.toString() ?? err.message}`);
            }
            fs.unlinkSync(advFile);
            console.log(`[${session}] ZIP deleted       : ${zipFilename}`);

            const newFiles = fs.readdirSync(OUTPUT_DIR)
              .filter((f: string) => !f.endsWith('.zip') && !beforeFiles.has(f))
              .map((f: string) => path.join(OUTPUT_DIR, f));

            if (newFiles.length === 0) {
              console.warn(`[${session}] ⚠ ZIP extracted 0 new files — extraction may have failed`);
            } else {
              console.log(`[${session}] Extracted ${newFiles.length} file(s) from ZIP:`);
              for (const f of newFiles) {
                const size = fs.statSync(f).size;
                console.log(`[${session}]   ${path.basename(f)} (${size.toLocaleString()} bytes)`);
                downloadedFiles.push(f);
              }
              advancedReportDownloaded = true;
            }
          }
        } else {
          console.log(`[${session}] Report found but no S3 URL yet — retrying`);
        }
      } else {
        console.log(`[${session}] Report not ready yet`);
      }

      if (!advancedReportDownloaded && attempt < 5) {
        console.log(`[${session}] Waiting 5 min before next attempt...`);
        await page.waitForTimeout(5 * 60_000);
      }
    }

    if (!advancedReportDownloaded) {
      console.warn(`[${session}] ⚠ Advanced report not found after 5 attempts`);
    }

    // ── 6. CONSOLIDATE via API ────────────────────────────────────────────────
    let consolidatedFile: string | null = null;
    if (advancedReportDownloaded) {
      console.log(`[${session}] ── Consolidation ─────────────────────────────────`);
      consolidatedFile = await consolidateViaAPI(OUTPUT_DIR, name, session);
      if (consolidatedFile) downloadedFiles.push(path.join(OUTPUT_DIR, consolidatedFile));
    }

    // ── 7. LOGOUT ─────────────────────────────────────────────────────────────
    await page.goto(`${BASE_URL}/accounts/logout/`, { waitUntil: 'domcontentloaded' });
    console.log(`[${session}] Logged out`);

    // ── 8. SUMMARY ────────────────────────────────────────────────────────────
    console.log(`[${session}] ── Summary ───────────────────────────────────────`);
    console.log(`[${session}] Files ready (${downloadedFiles.length}):`);
    for (const f of downloadedFiles) {
      const size = fs.existsSync(f) ? fs.statSync(f).size : 0;
      console.log(`[${session}]   ${path.basename(f)} (${size.toLocaleString()} bytes)`);
    }
    if (!consolidatedFile) {
      console.warn(`[${session}] ⚠ No consolidated output produced`);
    }

    return { advancedReportName: name, downloadedFiles };
  },
);
