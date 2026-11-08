import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * DemoGuidee — Démonstration automatique de Bourbon.IA, avant la prise en main.
 *
 * Un « bot » présente les bases de l'outil : la différence entre les trois
 * façons de charger des amendements et le bouton de classement, puis il charge
 * lui-même le jeu d'exemple, lance le tri sans IA et explique chaque colonne
 * du tableau. La zone commentée est mise en lumière. Lecture automatique, avec
 * pause, retour, suite et sortie à tout moment ; à la fin, la main est rendue.
 *
 * Volontairement inoffensive : aucune donnée envoyée à l'IA ou au cloud, rien
 * de supprimé — le bouton « Lancer le classement IA » est montré, jamais cliqué.
 *
 * Les zones ciblées portent un attribut `data-demo="…"` ; plusieurs éléments
 * peuvent porter le même nom (ex. deux en-têtes de colonne), le cadre les
 * englobe alors tous.
 */

const DUREE_PAR_DEFAUT = 8000

const ETAPES = [
  {
    titre: 'Bienvenue dans Bourbon.IA',
    texte: "Bourbon.IA aide les administrateurs de la séance à trier les amendements d'un texte de loi. Je vous montre l'essentiel en deux minutes, puis vous prenez la main.",
    duree: 6000,
  },
  {
    cible: 'btn-assemblee',
    titre: '1. « Depuis l’Assemblée »',
    texte: "La voie la plus simple : vous cherchez un dossier législatif par son titre, vous choisissez l'étape (commission ou séance plénière), et ses amendements arrivent directement depuis les données ouvertes de l'Assemblée. Aucun fichier à télécharger.",
    duree: 10000,
  },
  {
    cible: 'btn-json',
    titre: '2. « Importer un fichier JSON »',
    texte: "Si vous avez déjà les amendements dans un fichier — un export de data.assemblee-nationale.fr ou une sauvegarde de Bourbon.IA — vous le sélectionnez sur votre poste. Plusieurs fichiers peuvent être chargés d'un coup.",
    duree: 9000,
  },
  {
    cible: 'btn-coller',
    titre: '3. « Coller du JSON »',
    texte: "Pour quelques amendements copiés depuis un autre outil : vous collez directement le texte JSON dans une zone de saisie, sans passer par un fichier.",
    duree: 8000,
  },
  {
    cible: 'classer',
    titre: '4. « Lancer le classement IA »',
    texte: "Les trois boutons précédents CHARGENT les amendements ; celui-ci les CLASSE. Il applique d'abord les règles de l'Assemblée (instantané), puis confie les cas ambigus à l'IA, qui décide « discussion commune » ou « isolé ». En ligne, une alerte prévient avant tout envoi vers le cloud.",
    duree: 11000,
  },
  {
    cible: 'tableau',
    titre: 'Chargement de l’exemple',
    texte: "Pour la démo, je charge le jeu d'exemple : les amendements déposés en commission sur le projet de loi relatif aux jeux Olympiques et Paralympiques de 2030.",
    action: 'chargerExemple',
    duree: 7000,
  },
  {
    cible: 'bilan',
    titre: 'Tri instantané, sans IA',
    texte: "Je lance seulement la première partie du classement : les règles de l'Assemblée, sans IA. En moins d'une seconde, près de la moitié des amendements est classée. Les « en attente d'IA » sont ceux que « Lancer le classement IA » traiterait ensuite. Chaque tuile filtre le tableau d'un clic.",
    action: 'trierSansIA',
    duree: 11000,
  },
  {
    cible: 'col-art-num',
    titre: 'Colonnes « Art. » et « N° »',
    texte: "L'article du texte visé par l'amendement (« Avant/Après » pour un article additionnel), et le numéro de l'amendement. Le préfixe indique la commission : AC = affaires culturelles, CD = développement durable, CL = lois… ; sans préfixe, il est déposé en séance plénière.",
    duree: 10000,
  },
  {
    cible: 'col-auteur-groupe',
    titre: 'Colonnes « Auteur(s) » et « Groupe »',
    texte: "Le député qui a déposé l'amendement, et son groupe politique (LFI-NFP, EPR, RN, SOC…). Un rapporteur ou le Gouvernement peuvent aussi être auteurs.",
    duree: 8000,
  },
  {
    cible: 'col-impact',
    titre: 'Colonne « Point d’impact »',
    texte: "Ce que l'amendement modifie, du plus large au plus fin : suppression de l'article, réécriture de l'article, suppression ou réécriture d'un alinéa, ou point restreint (quelques mots). C'est ce qui fixe l'ordre d'appel en séance.",
    duree: 10000,
  },
  {
    cible: 'col-commission',
    titre: 'Colonne « Commission / Thèmes »',
    texte: "La commission où l'amendement a été déposé — ou « Séance plénière » — et, en étiquettes, les thèmes de cette commission retrouvés dans le texte de l'amendement.",
    duree: 9000,
  },
  {
    cible: 'col-extrait',
    titre: 'Colonne « Extrait du dispositif »',
    texte: "Le début du texte de l'amendement, c'est-à-dire la modification proposée. « Voir plus » affiche le texte complet ; un clic sur la ligne ouvre la fiche détaillée sous le tableau.",
    duree: 9000,
  },
  {
    cible: 'col-statut',
    titre: 'Colonne « Statut »',
    texte: "Le résultat du classement : Identique (même texte, auteurs différents), Doublon (même texte, même auteur), Discussion commune (amendements concurrents sur le même passage), Isolé (seul sur son passage). L'ampoule 💡 explique le raisonnement.",
    duree: 11000,
  },
  {
    cible: 'col-actions',
    titre: 'Colonne « Actions »',
    texte: "« Retirer » enlève un amendement de la liasse de travail (sans toucher aux données de l'Assemblée).",
    duree: 7000,
  },
  {
    titre: 'À vous !',
    texte: "Les amendements d'exemple restent chargés : lancez le classement IA, ouvrez une fiche, ou importez votre propre dossier. Vous pouvez revoir cette démo avec le bouton « ▶ Démo guidée » en haut de page.",
    duree: 0,
  },
]

// Rectangle englobant tous les éléments portant ce nom (null si aucun n'est affiché).
function cadreDe(nom) {
  if (!nom) return null
  const rects = [...document.querySelectorAll(`[data-demo="${nom}"]`)]
    .map((el) => el.getBoundingClientRect())
    .filter((r) => r.width > 0 && r.height > 0)
  if (rects.length === 0) return null
  const top = Math.min(...rects.map((r) => r.top))
  const left = Math.min(...rects.map((r) => r.left))
  return {
    top,
    left,
    width: Math.max(...rects.map((r) => r.right)) - left,
    height: Math.max(...rects.map((r) => r.bottom)) - top,
  }
}

export default function DemoGuidee({ actions, onTerminer }) {
  const [index, setIndex] = useState(0)
  const [enPause, setEnPause] = useState(false)
  const [enCours, setEnCours] = useState(false)
  const [cadre, setCadre] = useState(null)
  const faites = useRef(new Set())
  const actionsRef = useRef(actions)
  actionsRef.current = actions
  const monte = useRef(true)
  useEffect(() => {
    monte.current = true
    return () => { monte.current = false }
  }, [])

  const etape = ETAPES[index]
  const derniere = index === ETAPES.length - 1

  // Action de l'étape, exécutée une seule fois (revenir en arrière ne la rejoue pas).
  useEffect(() => {
    const nom = etape.action
    const action = nom && actionsRef.current[nom]
    if (!action || faites.current.has(nom)) return
    faites.current.add(nom)
    setEnCours(true)
    Promise.resolve()
      .then(action)
      .catch((err) => console.warn(`Démo : étape « ${nom} » ignorée`, err))
      .finally(() => { if (monte.current) setEnCours(false) })
  }, [etape])

  // Mise en lumière : suit la zone ciblée (défilement, redimensionnement, rendu tardif).
  useEffect(() => {
    let raf = 0
    let defile = false
    function suivre() {
      const r = cadreDe(etape.cible)
      if (r && !defile) {
        document.querySelector(`[data-demo="${etape.cible}"]`)
          ?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
        defile = true
      }
      setCadre((prec) =>
        prec && r && prec.top === r.top && prec.left === r.left && prec.width === r.width && prec.height === r.height
          ? prec
          : r
      )
      raf = requestAnimationFrame(suivre)
    }
    suivre()
    return () => cancelAnimationFrame(raf)
  }, [etape])

  // On n'avance pas pendant qu'une action du bot est en cours.
  const suivante = useCallback(() => {
    if (enCours) return
    if (derniere) onTerminer()
    else setIndex((i) => i + 1)
  }, [enCours, derniere, onTerminer])

  // Lecture automatique (suspendue en pause et pendant une action).
  useEffect(() => {
    const duree = etape.duree ?? DUREE_PAR_DEFAUT
    if (enPause || enCours || !duree) return
    const minuteur = setTimeout(suivante, duree)
    return () => clearTimeout(minuteur)
  }, [etape, enPause, enCours, suivante])

  // Clavier : Échap quitte, flèches naviguent, espace met en pause.
  useEffect(() => {
    function touche(e) {
      if (e.key === 'Escape') onTerminer()
      else if (e.key === 'ArrowRight') suivante()
      else if (e.key === 'ArrowLeft') setIndex((i) => Math.max(0, i - 1))
      else if (e.key === ' ' && e.target === document.body) { e.preventDefault(); setEnPause((p) => !p) }
    }
    window.addEventListener('keydown', touche)
    return () => window.removeEventListener('keydown', touche)
  }, [suivante, onTerminer])

  const marge = 8
  const bouton = 'rounded-md px-3 py-1.5 text-xs sm:text-sm font-medium transition-colors disabled:opacity-40'

  return (
    <div className="fixed inset-0 z-[9000] pointer-events-none" aria-live="polite">
      {/* Voile + projecteur sur la zone commentée */}
      {cadre ? (
        <div
          className="absolute rounded-lg ring-4 ring-[#D91227]"
          style={{
            top: cadre.top - marge,
            left: cadre.left - marge,
            width: cadre.width + marge * 2,
            height: cadre.height + marge * 2,
            boxShadow: '0 0 0 9999px rgba(11, 12, 16, 0.55)',
          }}
        />
      ) : (
        <div className="absolute inset-0" style={{ backgroundColor: 'rgba(11, 12, 16, 0.55)' }} />
      )}

      {/* Carte du narrateur */}
      <div
        role="dialog"
        aria-label="Démo guidée de Bourbon.IA"
        className="pointer-events-auto absolute bottom-4 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-xl rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#1A1B22] shadow-2xl p-4 sm:p-5"
      >
        <div className="flex items-start justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-[#D91227]">
            🤖 Démo guidée · étape {index + 1} / {ETAPES.length}
          </p>
          <button
            type="button"
            onClick={onTerminer}
            aria-label="Quitter la démo"
            className="text-slate-400 hover:text-slate-700 dark:hover:text-white text-lg leading-none"
          >
            ×
          </button>
        </div>
        <h2 className="mt-1 text-base sm:text-lg font-bold text-slate-900 dark:text-white">{etape.titre}</h2>
        <p className="mt-1.5 text-sm leading-relaxed text-slate-700 dark:text-slate-300">{etape.texte}</p>
        {enCours && <p className="mt-2 text-xs text-slate-500 dark:text-slate-400 animate-pulse">Le bot travaille…</p>}

        {/* Barre de progression */}
        <div className="mt-3 h-1 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
          <div className="h-full bg-[#D91227] transition-all duration-300" style={{ width: `${((index + 1) / ETAPES.length) * 100}%` }} />
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
          <button type="button" onClick={onTerminer} className={`${bouton} text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white`}>
            Passer la démo
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={index === 0}
              onClick={() => setIndex((i) => Math.max(0, i - 1))}
              className={`${bouton} border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800`}
            >
              ← Précédent
            </button>
            {!derniere && (
              <button
                type="button"
                onClick={() => setEnPause((p) => !p)}
                className={`${bouton} border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800`}
              >
                {enPause ? '▶ Reprendre' : '⏸ Pause'}
              </button>
            )}
            <button
              type="button"
              onClick={suivante}
              disabled={enCours}
              className={`${bouton} bg-[#D91227] text-white hover:bg-[#b80f21]`}
            >
              {derniere ? 'Commencer à utiliser Bourbon.IA' : 'Suivant →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
