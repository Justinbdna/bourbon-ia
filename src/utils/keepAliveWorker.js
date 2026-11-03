/**
 * src/utils/keepAliveWorker.js — Neutralisation de l'App Nap et de la mise en veille Safari
 * =========================================================================================
 * Safari et macOS suspendent ou brident agressivement les onglets d'arrière-plan ("App Nap"),
 * causant des interruptions de 2 à 4 minutes lors des traitements LLM en local.
 *
 * Ce module combine deux mécanismes de protection de premier ordre :
 * 1. Un Web Worker cadencé à 250 ms (exécuté sur un thread OS isolé qui ne subit pas le gel UI).
 * 2. Un AudioContext silencieux à gain nul (identifie l'onglet comme lecteur multimédia actif sous macOS).
 */

let workerInstance = null
let audioContextInstance = null
let silenceSourceInstance = null

const WORKER_BLOB_CODE = `
let intervalId = null;
self.onmessage = function(e) {
  if (e.data === 'start') {
    if (intervalId) clearInterval(intervalId);
    intervalId = setInterval(function() {
      self.postMessage({ type: 'tick', timestamp: Date.now() });
    }, 250);
  } else if (e.data === 'stop') {
    if (intervalId) clearInterval(intervalId);
    intervalId = null;
  }
};
`

/**
 * Démarre le cadencement d'arrière-plan et le maintien d'éveil anti-App Nap.
 * @param {Function} [onTick] Callback optionnel invoqué à chaque impulsion (250 ms)
 */
export function startKeepAlive(onTick) {
  // 1. Initialisation de l'AudioContext silencieux (anti-App Nap macOS/WebKit)
  try {
    const AudioCtxClass = (typeof window !== 'undefined' && (window.AudioContext || window.webkitAudioContext)) ||
                          (typeof globalThis !== 'undefined' && (globalThis.AudioContext || globalThis.webkitAudioContext))
    if (AudioCtxClass && !audioContextInstance) {
      audioContextInstance = new AudioCtxClass()
      // Buffer muet d'une seconde en boucle
      const sampleRate = audioContextInstance.sampleRate || 22050
      const buffer = audioContextInstance.createBuffer(1, sampleRate, sampleRate)
      silenceSourceInstance = audioContextInstance.createBufferSource()
      silenceSourceInstance.buffer = buffer
      silenceSourceInstance.loop = true

      const gainNode = audioContextInstance.createGain()
      gainNode.gain.value = 0.00001 // Quasiment inaudible / gain nul
      silenceSourceInstance.connect(gainNode)
      gainNode.connect(audioContextInstance.destination)

      silenceSourceInstance.start()
      if (audioContextInstance.state === 'suspended') {
        audioContextInstance.resume().catch(() => {})
      }
    }
  } catch (e) {
    // AudioContext peut être restreint avant interaction utilisateur directe
    console.debug('[KeepAlive] AudioContext keep-alive non actif :', e.message)
  }

  // 2. Initialisation du Web Worker autonome
  try {
    const WorkerClass = (typeof Worker !== 'undefined' && Worker) ||
                        (typeof globalThis !== 'undefined' && globalThis.Worker)
    if (WorkerClass && !workerInstance) {
      const blob = new Blob([WORKER_BLOB_CODE], { type: 'application/javascript' })
      const workerUrl = (typeof URL !== 'undefined' && URL.createObjectURL)
        ? URL.createObjectURL(blob)
        : 'blob:test'
      workerInstance = new WorkerClass(workerUrl)

      workerInstance.onmessage = (event) => {
        if (event.data?.type === 'tick' && typeof onTick === 'function') {
          onTick(event.data.timestamp)
        }
      }

      workerInstance.postMessage('start')
    }
  } catch (e) {
    console.debug('[KeepAlive] Web Worker keep-alive non actif :', e.message)
  }
}

/**
 * Arrête et libère toutes les ressources d'arrière-plan.
 */
export function stopKeepAlive() {
  if (workerInstance) {
    try {
      workerInstance.postMessage('stop')
      workerInstance.terminate()
    } catch {
      // ignore
    }
    workerInstance = null
  }

  if (silenceSourceInstance) {
    try {
      silenceSourceInstance.stop()
      silenceSourceInstance.disconnect()
    } catch {
      // ignore
    }
    silenceSourceInstance = null
  }

  if (audioContextInstance) {
    try {
      if (audioContextInstance.state !== 'closed') {
        audioContextInstance.close().catch(() => {})
      }
    } catch {
      // ignore
    }
    audioContextInstance = null
  }
}
