import { handlers } from './handlers'

let worker: any = null
if (typeof window !== 'undefined') {
  const { setupWorker } = require('msw/browser')
  worker = setupWorker(...handlers)
}

export { worker }
