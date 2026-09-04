import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'

import {
  backendArguments,
  findVirtualEnvironmentPython,
  forwardSignal,
  parseCliArgs,
  validateProjectFiles,
} from '../../scripts/run-local-app.mjs'

test('discovers POSIX and Windows virtual-environment interpreters', () => {
  const root = mkdtempSync(path.join(tmpdir(), 'running-coach-launcher-'))
  assert.equal(findVirtualEnvironmentPython(root, 'linux'), null)
  const posixPython = path.join(root, '.venv', 'bin', 'python3')
  const windowsPython = path.join(root, '.venv', 'Scripts', 'python.exe')
  mkdirSync(path.dirname(posixPython), { recursive: true })
  mkdirSync(path.dirname(windowsPython), { recursive: true })
  writeFileSync(posixPython, '')
  writeFileSync(windowsPython, '')

  assert.equal(findVirtualEnvironmentPython(root, 'darwin'), posixPython)
  assert.equal(findVirtualEnvironmentPython(root, 'win32'), windowsPython)
})

test('reports missing backend and compiled frontend prerequisites', () => {
  const root = mkdtempSync(path.join(tmpdir(), 'running-coach-launcher-'))
  assert.throws(() => validateProjectFiles(root), /Backend package source is missing/)

  const backend = path.join(root, 'src', 'running_coach_app')
  mkdirSync(backend, { recursive: true })
  writeFileSync(path.join(backend, '__init__.py'), '')
  assert.throws(() => validateProjectFiles(root), /Compiled frontend is missing/)
})

test('parses and forwards a custom port', () => {
  const options = parseCliArgs(['--port', '8123', '--open'])
  assert.deepEqual(options, { dev: false, open: true, port: 8123 })
  assert.deepEqual(backendArguments(options), [
    '-m',
    'running_coach_app.server',
    '--port',
    '8123',
    '--open',
  ])
})

test('forwards shutdown signals to all live child processes', () => {
  const received = []
  const child = {
    exitCode: null,
    killed: false,
    kill(signal) {
      received.push(signal)
    },
  }
  const exitedChild = { exitCode: 0, killed: false, kill() {} }

  forwardSignal([child, exitedChild], 'SIGTERM')

  assert.deepEqual(received, ['SIGTERM'])
})
