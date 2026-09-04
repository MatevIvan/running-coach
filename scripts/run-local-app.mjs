import { existsSync } from 'node:fs'
import { spawn, spawnSync } from 'node:child_process'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath, pathToFileURL } from 'node:url'

export const DEFAULT_PORT = 8000
export const LOOPBACK_HOST = '127.0.0.1'

export function parseCliArgs(argv) {
  const options = { dev: false, open: false, port: DEFAULT_PORT }

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === '--dev') {
      options.dev = true
    } else if (argument === '--open') {
      options.open = true
    } else if (argument === '--port') {
      const value = argv[index + 1]
      if (!value) {
        throw new Error('--port requires a value.')
      }
      options.port = Number(value)
      index += 1
    } else {
      throw new Error(`Unknown option: ${argument}`)
    }
  }

  if (!Number.isInteger(options.port) || options.port < 1 || options.port > 65535) {
    throw new Error('--port must be an integer between 1 and 65535.')
  }

  return options
}

export function virtualEnvironmentCandidates(projectRoot, platform = process.platform) {
  if (platform === 'win32') {
    return [
      path.join(projectRoot, '.venv', 'Scripts', 'python.exe'),
      path.join(projectRoot, '.venv', 'Scripts', 'python3.exe'),
    ]
  }
  return [
    path.join(projectRoot, '.venv', 'bin', 'python3'),
    path.join(projectRoot, '.venv', 'bin', 'python'),
  ]
}

export function findVirtualEnvironmentPython(
  projectRoot,
  platform = process.platform,
  fileExists = existsSync,
) {
  return virtualEnvironmentCandidates(projectRoot, platform).find(fileExists) ?? null
}

export function validateProjectFiles(projectRoot, { requireBuild = true } = {}) {
  const backendSource = path.join(projectRoot, 'src', 'running_coach_app', '__init__.py')
  if (!existsSync(backendSource)) {
    throw new Error(`Backend package source is missing at ${backendSource}.`)
  }

  if (requireBuild) {
    const frontendIndex = path.join(projectRoot, 'frontend', 'dist', 'index.html')
    if (!existsSync(frontendIndex)) {
      throw new Error(
        `Compiled frontend is missing at ${frontendIndex}. Run the initialization skill or \`npm run build\`.`,
      )
    }
  }
}

export function backendArguments(options) {
  const args = ['-m', 'running_coach_app.server', '--port', String(options.port)]
  if (options.open) {
    args.push('--open')
  }
  if (options.dev) {
    args.push('--reload')
  }
  return args
}

export function forwardSignal(children, signal) {
  for (const child of children) {
    if (child && child.exitCode === null && !child.killed) {
      child.kill(signal)
    }
  }
}

function assertBackendInstalled(python, projectRoot) {
  const check = spawnSync(
    python,
    ['-c', 'import running_coach_app, fastapi, uvicorn'],
    { cwd: projectRoot, encoding: 'utf8' },
  )
  if (check.status !== 0) {
    throw new Error(
      'The backend package is not installed in .venv. Run the initialization skill or `.venv/bin/python -m pip install -e .` (Windows: `.venv\\Scripts\\python.exe -m pip install -e .`).',
    )
  }
}

function npmInvocation(args) {
  if (process.env.npm_execpath) {
    return { command: process.execPath, args: [process.env.npm_execpath, ...args] }
  }
  return { command: process.platform === 'win32' ? 'npm.cmd' : 'npm', args }
}

async function runDevelopment(python, projectRoot, options, environment) {
  const backend = spawn(python, backendArguments(options), {
    cwd: projectRoot,
    env: environment,
    stdio: 'inherit',
  })
  const viteArgs = ['run', 'dev', '--workspace', 'frontend']
  if (options.open) {
    viteArgs.push('--', '--open')
  }
  const npm = npmInvocation(viteArgs)
  const frontend = spawn(npm.command, npm.args, {
    cwd: projectRoot,
    env: environment,
    stdio: 'inherit',
  })
  const children = [backend, frontend]

  return await new Promise((resolve) => {
    let settled = false
    const finish = (code, signal) => {
      if (settled) return
      settled = true
      forwardSignal(children, signal === 'SIGINT' ? 'SIGINT' : 'SIGTERM')
      resolve(code ?? (signal ? 1 : 0))
    }

    backend.once('exit', finish)
    frontend.once('exit', finish)
    process.once('SIGINT', () => finish(0, 'SIGINT'))
    process.once('SIGTERM', () => finish(0, 'SIGTERM'))
  })
}

async function runProduction(python, projectRoot, options, environment) {
  const child = spawn(python, backendArguments(options), {
    cwd: projectRoot,
    env: environment,
    stdio: 'inherit',
  })

  return await new Promise((resolve) => {
    let shutdownRequested = false
    const stopWith = (signal) => {
      shutdownRequested = true
      forwardSignal([child], signal)
    }
    const stopWithInterrupt = () => stopWith('SIGINT')
    const stopWithTermination = () => stopWith('SIGTERM')

    process.once('SIGINT', stopWithInterrupt)
    process.once('SIGTERM', stopWithTermination)
    child.once('exit', (code, signal) => {
      process.removeListener('SIGINT', stopWithInterrupt)
      process.removeListener('SIGTERM', stopWithTermination)
      resolve(shutdownRequested ? 0 : (code ?? (signal ? 1 : 0)))
    })
  })
}

export async function main(argv = process.argv.slice(2)) {
  const projectRoot = path.resolve(fileURLToPath(new URL('..', import.meta.url)))
  const options = parseCliArgs(argv)
  const python = findVirtualEnvironmentPython(projectRoot)
  if (!python) {
    throw new Error(
      'Project virtual environment not found. Run the initialize-running-project skill first.',
    )
  }

  validateProjectFiles(projectRoot, { requireBuild: !options.dev })
  assertBackendInstalled(python, projectRoot)

  const environment = {
    ...process.env,
    RUNNING_COACH_API_PORT: String(options.port),
    RUNNING_COACH_PROJECT_ROOT: projectRoot,
  }
  const url = `http://${LOOPBACK_HOST}:${options.port}`
  console.log(options.dev ? `Backend: ${url}` : `Running Coach: ${url}`)

  return options.dev
    ? await runDevelopment(python, projectRoot, options, environment)
    : await runProduction(python, projectRoot, options, environment)
}

const invokedPath = process.argv[1] ? pathToFileURL(path.resolve(process.argv[1])).href : ''
if (invokedPath === import.meta.url) {
  main()
    .then((code) => {
      process.exitCode = code
    })
    .catch((error) => {
      console.error(`Unable to start Running Coach: ${error.message}`)
      process.exitCode = 1
    })
}
