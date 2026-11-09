/**
 * serveur.js — Adresse du serveur Bourbon.IA et envoi des requêtes.
 *
 * Deux modes, au choix de l'utilisateur (⚙️ Réglages IA → Serveur Bourbon.IA) :
 *   • « en ligne » : le serveur qui sert l'application (Vercel en démo) ;
 *   • « local »    : un serveur lancé sur le poste (http://localhost:8000).
 *     Les amendements ne passent alors plus par le serveur en ligne, et la
 *     limite de taille de Vercel ne s'applique pas.
 *
 * Les gros envois (au-delà de SEUIL_COMPRESSION) sont compressés en gzip :
 * Vercel refuse toute requête de plus de 4,5 Mo, soit ~600 amendements non
 * compressés (cf. api/transport.py côté serveur).
 */

export const SERVEUR_LOCAL = 'http://localhost:8000'
const SERVEUR_EN_LIGNE = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000')
const CLE_SERVEUR = 'bourbon_serveur'
const SEUIL_COMPRESSION = 20 * 1024

/** Mode choisi : 'en_ligne' (par défaut) ou 'local'. */
export function modeServeur() {
  try {
    return localStorage.getItem(CLE_SERVEUR) === 'local' ? 'local' : 'en_ligne'
  } catch {
    return 'en_ligne'
  }
}

export function choisirServeur(mode) {
  try {
    localStorage.setItem(CLE_SERVEUR, mode === 'local' ? 'local' : 'en_ligne')
  } catch {
    // stockage indisponible : le choix ne survit pas au rechargement
  }
}

/** Adresse de base des appels d'API (chaîne vide = même origine que le site). */
export function apiBase() {
  return modeServeur() === 'local' ? SERVEUR_LOCAL : SERVEUR_EN_LIGNE
}

async function compresser(texte) {
  const flux = new Blob([texte]).stream().pipeThrough(new CompressionStream('gzip'))
  return await new Response(flux).arrayBuffer()
}

/** POST JSON vers le serveur Bourbon.IA, compressé en gzip au-delà de 20 Ko. */
export async function postJSON(chemin, donnees, options = {}) {
  const texte = JSON.stringify(donnees)
  const headers = { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' }
  let body = texte
  if (texte.length > SEUIL_COMPRESSION && typeof CompressionStream !== 'undefined') {
    body = await compresser(texte)
    headers['Content-Encoding'] = 'gzip'
  }
  return fetch(`${apiBase()}${chemin}`, { method: 'POST', headers, body, signal: options.signal })
}

/** Vérifie qu'un serveur Bourbon.IA répond à cette adresse (GET /api/health). */
export async function testerServeur(base) {
  const controller = new AbortController()
  const minuteur = setTimeout(() => controller.abort(), 4000)
  try {
    const res = await fetch(`${base}/api/health`, { signal: controller.signal })
    return res.ok && (await res.json()).status === 'ok'
  } catch {
    return false
  } finally {
    clearTimeout(minuteur)
  }
}
