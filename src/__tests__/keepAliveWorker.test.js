import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { startKeepAlive, stopKeepAlive } from '../utils/keepAliveWorker'

describe('keepAliveWorker.js — Cadencement d\'arrière-plan sans audio', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    stopKeepAlive()
  })

  afterEach(() => {
    stopKeepAlive()
  })

  it('startKeepAlive et stopKeepAlive s\'exécutent sans erreur en environnement sans Web Worker', () => {
    expect(() => startKeepAlive()).not.toThrow()
    expect(() => stopKeepAlive()).not.toThrow()
  })

  it('ne comporte aucune référence d\'AudioContext ni ne génère de flux sonore', () => {
    const audioCtxSpy = vi.fn()
    globalThis.AudioContext = audioCtxSpy
    if (typeof window !== 'undefined') window.AudioContext = audioCtxSpy

    startKeepAlive()
    expect(audioCtxSpy).not.toHaveBeenCalled()
    stopKeepAlive()
  })

  it('startKeepAlive initialise un Worker et stopKeepAlive appelle terminate()', () => {
    const mockPostMessage = vi.fn()
    const mockTerminate = vi.fn()
    class MockWorker {
      constructor() {
        this.postMessage = mockPostMessage
        this.terminate = mockTerminate
      }
    }

    const originalWorker = globalThis.Worker
    const originalCreateObjectURL = globalThis.URL?.createObjectURL

    globalThis.Worker = MockWorker
    if (typeof window !== 'undefined') {
      window.Worker = MockWorker
    }
    if (!globalThis.URL) globalThis.URL = {}
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue('blob:test')

    try {
      startKeepAlive()
      expect(mockPostMessage).toHaveBeenCalledWith('start')

      stopKeepAlive()
      expect(mockTerminate).toHaveBeenCalled()
      expect(mockPostMessage).toHaveBeenCalledWith('stop')
    } finally {
      globalThis.Worker = originalWorker
      if (typeof window !== 'undefined') {
        window.Worker = originalWorker
      }
      if (originalCreateObjectURL) {
        globalThis.URL.createObjectURL = originalCreateObjectURL
      }
    }
  })
})
