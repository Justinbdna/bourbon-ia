import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { startKeepAlive, stopKeepAlive } from '../utils/keepAliveWorker'

describe('keepAliveWorker.js — Neutralisation App Nap et veille Safari', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    stopKeepAlive()
  })

  afterEach(() => {
    stopKeepAlive()
  })

  it('startKeepAlive et stopKeepAlive s\'exécutent sans erreur en environnement sans Web Audio / Worker', () => {
    expect(() => startKeepAlive()).not.toThrow()
    expect(() => stopKeepAlive()).not.toThrow()
  })

  it('startKeepAlive initialise un AudioContext et un Worker quand disponibles', () => {
    const mockPostMessage = vi.fn()
    const mockTerminate = vi.fn()
    class MockWorker {
      constructor() {
        this.postMessage = mockPostMessage
        this.terminate = mockTerminate
      }
    }

    const mockStart = vi.fn()
    const mockStop = vi.fn()
    const mockDisconnect = vi.fn()
    const mockConnect = vi.fn()
    const mockCreateBuffer = vi.fn().mockReturnValue({})
    const mockCreateBufferSource = vi.fn().mockReturnValue({
      buffer: null,
      loop: false,
      connect: mockConnect,
      start: mockStart,
      stop: mockStop,
      disconnect: mockDisconnect,
    })
    const mockCreateGain = vi.fn().mockReturnValue({
      gain: { value: 1 },
      connect: mockConnect,
    })

    class MockAudioContext {
      constructor() {
        this.sampleRate = 44100
        this.state = 'running'
        this.destination = {}
        this.createBuffer = mockCreateBuffer
        this.createBufferSource = mockCreateBufferSource
        this.createGain = mockCreateGain
        this.close = vi.fn().mockResolvedValue(undefined)
      }
    }

    const originalWorker = globalThis.Worker
    const originalAudioContext = globalThis.AudioContext
    const originalCreateObjectURL = globalThis.URL?.createObjectURL

    globalThis.Worker = MockWorker
    globalThis.AudioContext = MockAudioContext
    if (typeof window !== 'undefined') {
      window.Worker = MockWorker
      window.AudioContext = MockAudioContext
    }
    if (!globalThis.URL) globalThis.URL = {}
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue('blob:test')

    try {
      startKeepAlive()
      expect(mockStart).toHaveBeenCalled()
      expect(mockPostMessage).toHaveBeenCalledWith('start')

      stopKeepAlive()
      expect(mockTerminate).toHaveBeenCalled()
      expect(mockStop).toHaveBeenCalled()
    } finally {
      globalThis.Worker = originalWorker
      globalThis.AudioContext = originalAudioContext
      if (typeof window !== 'undefined') {
        window.Worker = originalWorker
        window.AudioContext = originalAudioContext
      }
      if (originalCreateObjectURL) {
        globalThis.URL.createObjectURL = originalCreateObjectURL
      }
    }
  })
})
