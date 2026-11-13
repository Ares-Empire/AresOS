import {SandboxManager} from '@anthropic-ai/sandbox-runtime';
import {readFileSync} from 'node:fs';
import {spawn} from 'node:child_process';

// Only the trusted test harness invokes this, never an arbitrary config path.
const nativeCanary = process.argv[2] === '--native-canary';
const config = JSON.parse(readFileSync('/opt/aresos-control/' + (nativeCanary ? 'native-canary.json' : 'sandbox.json'), 'utf8'));
try {
  await SandboxManager.initialize(config);
  const deps = await SandboxManager.checkDependenciesAsync();
  console.error('DEPENDENCIES ' + JSON.stringify(deps));
  const command = nativeCanary ? 'ARGV0=apply-seccomp /opt/aresos-control/node_modules/@anthropic-ai/claude-code-linux-x64/claude /usr/bin/python3 -I /opt/aresos-control/seccomp-canary.py' : process.argv[2];
  if (!command) throw new Error('missing fixed test command');
  const wrapped = await SandboxManager.wrapWithSandbox(command, '/bin/bash');
  console.error('WRAPPED ' + wrapped);
  const code = await new Promise((resolve, reject) => {
    const child = spawn('/bin/bash', ['-c', wrapped], {stdio: 'inherit'});
    child.on('error', reject);
    child.on('exit', (status, signal) => resolve(signal ? 128 : status));
  });
  process.exitCode = code;
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await SandboxManager.reset();
}
