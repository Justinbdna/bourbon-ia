#!/usr/bin/env python3
"""
Génération des 15 fichiers audio MP3 pour la Démo Guidée de Bourbon.IA.
Voix : fr-FR-DeniseNeural (voix féminine française, institutionnelle et fluide).
Sortie : public/audio/demo/etape-01.mp3 ... etape-15.mp3
"""
import asyncio
from pathlib import Path
import edge_tts

ETAPES_AUDIO = [
    (1, "Bienvenue dans Bourbon.IA. Bourbon.IA aide les administrateurs de la séance à trier les amendements d'un texte de loi. Je vous montre l'essentiel en deux minutes, puis vous prenez la main."),
    (2, "Première étape : Depuis l'Assemblée. La voie la plus simple : vous cherchez un dossier législatif par son titre, vous choisissez l'étape, commission ou séance plénière, et ses amendements arrivent directement depuis les données ouvertes de l'Assemblée nationale. Aucun fichier à télécharger."),
    (3, "Deuxième étape : Importer un fichier J-sonne. Si vous avez déjà les amendements dans un fichier, un export de data.assemblee-nationale.fr ou une sauvegarde de Bourbon.IA, vous le sélectionnez sur votre poste. Plusieurs fichiers peuvent être chargés d'un coup."),
    (4, "Troisième étape : Coller du J-sonne. Pour quelques amendements copiés depuis un autre outil : vous collez directement le texte J-sonne dans une zone de saisie, sans passer par un fichier."),
    (5, "Quatrième étape : Lancer le classement par intelligence artificielle. Les trois boutons précédents chargent les amendements ; celui-ci les classe. Il applique d'abord les règles de l'Assemblée, de manière instantanée, puis confie les cas ambigus à l'intelligence artificielle, qui décide discussion commune ou isolé. En ligne, une alerte prévient avant tout envoi vers le cloud."),
    (6, "Chargement de l'exemple. Pour la démonstration, je charge le jeu d'exemple : les amendements déposés en commission sur le projet de loi relatif aux jeux Olympiques et Paralympiques de 2030."),
    (7, "Tri instantané, sans intelligence artificielle. Je lance seulement la première partie du classement : les règles formelles de l'Assemblée, sans I.A. En moins d'une seconde, près de la moitié des amendements est classée. Les amendements indiqués en attente d'I.A. sont ceux que le classement par intelligence artificielle traiterait ensuite. Chaque tuile filtre le tableau d'un clic."),
    (8, "Colonnes Article et Numéro. L'article du texte visé par l'amendement, avant ou après pour un article additionnel, et le numéro de l'amendement. Le préfixe indique la commission : A.C. pour affaires culturelles, C.D. pour développement durable, C.L. pour lois ; sans préfixe, il est déposé en séance plénière."),
    (9, "Colonnes Auteurs et Groupe politique. Le député qui a déposé l'amendement, et son groupe politique : L.F.I.-N.F.P., E.P.R., R.N., Socialistes… Un rapporteur ou le Gouvernement peuvent également être auteurs."),
    (10, "Colonne Point d'impact. Ce que l'amendement modifie, du plus large au plus fin : suppression de l'article, réécriture de l'article, suppression ou réécriture d'un alinéa, ou point restreint portant sur quelques mots. C'est ce qui fixe l'ordre d'appel en séance."),
    (11, "Colonne Commission et Thèmes. La commission où l'amendement a été déposé, ou séance plénière, et, sous forme d'étiquettes, les thèmes de cette commission retrouvés dans le texte de l'amendement."),
    (12, "Colonne Extrait du dispositif. Le début du texte de l'amendement, c'est-à-dire la modification proposée. Le bouton Voir plus affiche le texte complet, et un clic sur la ligne ouvre la fiche détaillée sous le tableau."),
    (13, "Colonne Statut. Le résultat du classement : Identique pour un même texte avec des auteurs différents, Doublon pour un même texte avec le même auteur, Discussion commune pour des amendements concurrents sur un même passage, et Isolé s'il est seul sur son passage. L'ampoule explique le raisonnement."),
    (14, "Colonne Actions. Le bouton Retirer enlève un amendement de la liasse de travail, sans toucher aux données de l'Assemblée nationale."),
    (15, "À vous la parole ! Les amendements d'exemple restent chargés : lancez le classement par I.A., ouvrez une fiche, ou importez votre propre dossier. Vous pouvez revoir cette démonstration à tout moment grâce au bouton Démo guidée en haut de page."),
]

DOSSIER_SORTIE = Path(__file__).resolve().parent.parent / "public" / "audio" / "demo"
VOIX = "fr-FR-DeniseNeural"

async def generer():
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    print(f"🎙️ Génération des 15 fichiers audio avec la voix : {VOIX}")
    print(f"📁 Destination : {DOSSIER_SORTIE}")
    
    for numero, texte in ETAPES_AUDIO:
        fichier_mp3 = DOSSIER_SORTIE / f"etape-{numero:02d}.mp3"
        print(f"⏳ Génération étape {numero:02d}/15 -> {fichier_mp3.name}...")
        communicate = edge_tts.Communicate(texte, voice=VOIX, rate="+0%", pitch="+0Hz")
        await communicate.save(str(fichier_mp3))
        taille_ko = fichier_mp3.stat().st_size / 1024
        print(f"   ✓ Fait ({taille_ko:.1f} Ko)")
        
    print("\n🎉 Les 15 fichiers audio ont été générés avec succès !")

if __name__ == "__main__":
    asyncio.run(generer())

