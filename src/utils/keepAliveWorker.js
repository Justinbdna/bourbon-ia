/**
 * src/utils/keepAliveWorker.js — Cadencement d'arrière-plan sans aucun flux audio
 * ==============================================================================
 * Exécute un Web Worker autonome sur un thread OS isolé cadencé à 250 ms
 * pour empêcher Safari et WebKit de suspendre la file asynchrone lors du traitement.
 *
 * NOTE IMPORTANTE : Tout hack d'AudioContext / Web Audio est STRICTEMENT PROSCRIT
 * afin d'éviter l'apparition de l'icône haut-parleur (🔊) dans l'onglet du navigateur.
 */

let workerInstance = null

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
 * Démarre le Web Worker de pulsation d'arrière-plan.
 * @param {Function} [onTick] Callback optionnel invoqué à chaque impulsion (250 ms)
 */
export function startKeepAlive(onTick) {
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
 * Arrête immédiatement et termine le Web Worker d'arrière-plan.
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
}
