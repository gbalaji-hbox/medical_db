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

async function consolidateViaAPI(outputDir: string, reportName: string, session: string): Promise<void> {
  const allCsvs  = fs.readdirSync(outputDir).filter((f: string) => f.endsWith('.csv'));
  const medFile  = allCsvs.find((f: string) => f.startsWith('medication_report_'));
  const probFile = allCsvs.find((f: string) => f.startsWith('problem_report_'));
  const emrFile  = allCsvs.find((f: string) => f !== medFile && f !== probFile);

  if (!medFile || !probFile || !emrFile) {
    console.warn(`[${session}] Missing CSVs — skipping consolidation`);
    return;
  }

  // POST /api/xhi/process
  console.log(`[${session}] Submitting files to XHI API...`);
  const form = new FormData();
  form.append('emr_report',        new Blob([fs.readFileSync(path.join(outputDir, emrFile))],  { type: 'text/csv' }), emrFile);
  form.append('medication_report', new Blob([fs.readFileSync(path.join(outputDir, medFile))],  { type: 'text/csv' }), medFile);
  form.append('problem_report',    new Blob([fs.readFileSync(path.join(outputDir, probFile))], { type: 'text/csv' }), probFile);

  const submitRes = await fetch(`${API_BASE}/api/xhi/process`, { method: 'POST', headers: API_HEADERS, body: form });
  if (!submitRes.ok) throw new Error(`XHI submit failed ${submitRes.status}: ${await submitRes.text()}`);
  const { job_id } = await submitRes.json() as { job_id: string };
  console.log(`[${session}] XHI job queued — job_id: ${job_id}`);

  // Poll /api/xhi/jobs/{job_id}
  const DEADLINE_MS = Date.now() + 30 * 60_000;
  let status = '';
  while (Date.now() < DEADLINE_MS) {
    await new Promise(r => setTimeout(r, 15_000));
    const pollRes = await fetch(`${API_BASE}/api/xhi/jobs/${job_id}`, { headers: API_HEADERS });
    if (!pollRes.ok) throw new Error(`XHI poll failed ${pollRes.status}`);
    const job = await pollRes.json() as { status: string; error?: string };
    status = job.status;
    console.log(`[${session}] XHI job status: ${status}`);
    if (status === 'done') break;
    if (status === 'failed' || status === 'error') throw new Error(`XHI pipeline failed: ${job.error ?? status}`);
  }
  if (status !== 'done') throw new Error('XHI job timed out after 30 min');

  // GET /api/xhi/jobs/{job_id}/download
  console.log(`[${session}] Downloading consolidated file...`);
  const dlRes = await fetch(`${API_BASE}/api/xhi/jobs/${job_id}/download`, { headers: API_HEADERS });
  if (!dlRes.ok) throw new Error(`XHI download failed ${dlRes.status}`);
  const disposition = dlRes.headers.get('content-disposition') ?? '';
  const fnMatch = disposition.match(/filename="([^"]+)"/);
  const outName = fnMatch ? fnMatch[1] : `XHI_consolidated_${reportName}.xlsx`;
  fs.writeFileSync(path.join(outputDir, outName), Buffer.from(await dlRes.arrayBuffer()));
  console.log(`[${session}] ✅ Consolidated file saved: ${path.join(outputDir, outName)}`);
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
    const medFile    = path.join(OUTPUT_DIR, `medication_report_${name}.csv`);
    fs.writeFileSync(medFile, medCsvText);
    downloadedFiles.push(medFile);
    console.log(`[${session}] Medication report saved (${medCsvText.length} chars)`);

    // ── 4. PROBLEM REPORT — 5-year range ─────────────────────────────────────
    console.log(`[${session}] Fetching Problem Report CSV`);
    const probR       = await page.context().request.get(`${BASE_URL}/analytics/problem_report/export_csv?page=1&start_date=${encodeURIComponent(dateOffsetMMDDYYYY(5))}&end_date=${encodeURIComponent(today)}`, { timeout: 30_000 });
    const probCsvText = await probR.text();
    const probFile    = path.join(OUTPUT_DIR, `problem_report_${name}.csv`);
    fs.writeFileSync(probFile, probCsvText);
    downloadedFiles.push(probFile);
    console.log(`[${session}] Problem report saved (${probCsvText.length} chars)`);

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
          const s3Resp = await page.context().request.get(s3Url, { timeout: 60_000 });
          const advFile = path.join(OUTPUT_DIR, `${name}.zip`);
          fs.writeFileSync(advFile, await s3Resp.body());
          const { execSync } = await import('child_process');
          execSync(`powershell -Command "Expand-Archive -Path '${advFile}' -DestinationPath '${OUTPUT_DIR}' -Force"`, { stdio: 'pipe' });
          fs.unlinkSync(advFile);
          const extracted = fs.readdirSync(OUTPUT_DIR).filter((f: string) => !f.endsWith('.zip')).map((f: string) => path.join(OUTPUT_DIR, f));
          downloadedFiles.push(...extracted);
          console.log(`[${session}] Extracted: ${extracted.join(', ')}`);
          advancedReportDownloaded = true;
        } else {
          console.log(`[${session}] Report found but no S3 URL — retrying`);
        }
      } else {
        console.log(`[${session}] Report not ready yet`);
      }

      if (!advancedReportDownloaded && attempt < 5) {
        console.log(`[${session}] Waiting 5 min...`);
        await page.waitForTimeout(5 * 60_000);
      }
    }

    if (!advancedReportDownloaded) {
      console.warn(`[${session}] Advanced report not found after 5 attempts`);
    }

    // ── 6. CONSOLIDATE via API ────────────────────────────────────────────────
    if (advancedReportDownloaded) {
      console.log(`[${session}] Running XHI consolidation via API...`);
      await consolidateViaAPI(OUTPUT_DIR, name, session);
    }

    // ── 7. LOGOUT ─────────────────────────────────────────────────────────────
    await page.goto(`${BASE_URL}/accounts/logout/`, { waitUntil: 'domcontentloaded' });
    console.log(`[${session}] ✅ Done — ${downloadedFiles.length} file(s)`);
    return { advancedReportName: name, downloadedFiles };
  },
);
