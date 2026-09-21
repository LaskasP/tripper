import { spawn, spawnSync } from 'node:child_process';
import path from 'node:path';


const databaseUrl =
  'postgresql+psycopg_async://tripper:tripper@127.0.0.1:55432/tripper_test';
const testEnvironment = {
  ...process.env,
  TRIPPER_DATABASE_URL: databaseUrl,
  TRIPPER_TEST_DATABASE_URL: databaseUrl,
};
const python = path.join(
  process.cwd(),
  '.venv',
  process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
);

function run(command, args) {
  const result = spawnSync(command, args, {
    env: testEnvironment,
    stdio: 'inherit',
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

run('docker', ['compose', '-f', 'compose.test.yml', 'up', '-d', '--wait']);
run('python', ['-m', 'uv', 'run', 'alembic', 'upgrade', 'head']);

const api = spawn(
  python,
  ['-m', 'tests.e2e_server'],
  { env: testEnvironment, stdio: 'inherit' },
);

async function waitForApi() {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    if (api.exitCode !== null) {
      throw new Error(`The end-to-end API exited with code ${api.exitCode}.`);
    }
    try {
      const response = await fetch('http://127.0.0.1:18014/docs');
      if (response.ok) return;
    } catch {
      // The API is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error('The end-to-end API did not start.');
}

function runPlaywright() {
  return new Promise((resolve, reject) => {
    const test = spawn(
      process.execPath,
      ['node_modules/@playwright/test/cli.js', 'test', '--reporter=line'],
      { stdio: 'inherit' },
    );
    test.once('error', reject);
    test.once('exit', (code) => resolve(code ?? 1));
  });
}

let exitCode = 1;
try {
  await waitForApi();
  exitCode = await runPlaywright();
} finally {
  api.kill();
  await new Promise((resolve) => api.once('exit', resolve));
  spawnSync('docker', ['compose', '-f', 'compose.test.yml', 'down', '--volumes'], {
    stdio: 'inherit',
  });
}

process.exitCode = exitCode;
