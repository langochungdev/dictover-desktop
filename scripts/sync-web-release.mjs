import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');
const RELEASE_BASE = 'https://github.com/langochungdev/dictover-desktop/releases';

const changelogPath = path.join(ROOT_DIR, 'CHANGELOG.md');
const versionPath = path.join(ROOT_DIR, 'web', 'version.json');
const outputDir = path.join(ROOT_DIR, 'web', 'releases');
const outputPath = path.join(outputDir, 'latest.json');

function parseVersion(raw) {
  if (typeof raw !== 'string') {
    return '';
  }

  const value = raw.trim();
  return /^\d+\.\d+\.\d+$/.test(value) ? value : '';
}

function extractNotes(markdownSection) {
  const bulletMatches = [...markdownSection.matchAll(/^\s*-\s+(.+)$/gm)];
  return bulletMatches.map((match) => match[1].trim()).filter(Boolean);
}

function parseLatestChangelog(changelog) {
  const normalized = changelog.replace(/\r\n/g, '\n');
  const sectionMatch = normalized.match(/^##\s+v?(\d+\.\d+\.\d+)\s*-\s*([^\n]+)\n([\s\S]*?)(?=\n##\s+v?\d+\.\d+\.\d+\s*-|(?![\s\S]))/m);

  if (!sectionMatch) {
    return {
      version: '',
      publishedAt: '',
      markdown: '',
      notes: []
    };
  }

  const markdown = sectionMatch[3].trim();
  return {
    version: parseVersion(sectionMatch[1]),
    publishedAt: sectionMatch[2].trim(),
    markdown,
    notes: extractNotes(markdown)
  };
}

async function main() {
  const [versionRaw, changelogRaw] = await Promise.all([
    readFile(versionPath, 'utf8'),
    readFile(changelogPath, 'utf8')
  ]);

  const parsedVersion = parseVersion(JSON.parse(versionRaw)?.version);
  const latest = parseLatestChangelog(changelogRaw);
  const effectiveVersion = latest.version || parsedVersion;

  if (!effectiveVersion) {
    throw new Error('Cannot resolve release version from web/version.json or CHANGELOG.md');
  }

  const payload = {
    version: effectiveVersion,
    tag: `v${effectiveVersion}`,
    title: `DictOver v${effectiveVersion}`,
    publishedAt: latest.publishedAt,
    notes: latest.notes,
    notesMarkdown: latest.markdown,
    downloadUrl: `${RELEASE_BASE}/download/v${effectiveVersion}/DictOver-${effectiveVersion}.zip`,
    releaseUrl: `${RELEASE_BASE}/tag/v${effectiveVersion}`,
    generatedAt: new Date().toISOString()
  };

  await mkdir(outputDir, { recursive: true });
  await writeFile(outputPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');

  process.stdout.write(`Synced ${path.relative(ROOT_DIR, outputPath)} for v${effectiveVersion}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
});