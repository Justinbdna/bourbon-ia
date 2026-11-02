# Rapport d'Audit et de Qualification Légistique — 341 Amendements

> **Bourbon.ia — Moteur d'Ingénierie Légistique et Constitutionnelle**  
> *Source : `public/sample-amendments.json` | Volume audité : 341 amendements | Règlements AN & Sénat*

---

## Section 1 : Tableau de bord global (Métriques consolidées)

| Métrique d'audit | Valeur | Proportion | Commentaire légistique |
| :--- | :---: | :---: | :--- |
| **Amendements totaux analysés** | **341** | 100,0 % | Intégralité du corpus du projet de loi |
| **Alertes Article 40 (sans gage)** | **3** | 0.9 % | Risque d'irrecevabilité financière constitutionnelle |
| **Alertes non normatif (Art. 6 DDHC)** | **2** | 0.6 % | Neutrons législatifs dépourvus de portée contraignante |
| **Tri déterministe (identiques & doublons)** | **85** | 24.9 % | Traités mécaniquement à coût zéro (sans appel LLM) |
| ↳ *Identiques officiels (AN discussionIdentique)* | 52 | 15.2 % | Regroupés officiellement par les services de la séance |
| ↳ *Identiques mécaniques (empreinte texte)* | 33 | 9.7 % | Rapprochés par similarité exacte du texte dispositif |
| ↳ *Doublons mécaniques même auteur* | 0 | 0.0 % | Redéposés par le même député (à retirer) |
| **Conformité typographique JO (espaces & tirets)** | **222** | 75.0 % | Normalisation stricte selon les règles du Journal Officiel |

### Distribution des verbes d'action du chapeau

| Verbe d'action légistique | Amendements | Part relative | Règle de recevabilité associée |
| :--- | :---: | :---: | :--- |
| `INSERER` | 84 | 24.6 % | Création d'articles additionnels ou d'alinéas intercalés |
| `SUPPRIMER` | 79 | 23.2 % | Suppression totale d'articles ou d'alinéas ciblés (priorité haute au dérouleur) |
| `SUBSTITUER` | 72 | 21.1 % | Substitution chirurgicale de mots ou membres de phrase |
| `Sans dispositif (Retiré/Caduc)` | 45 | 13.2 % | Amendements déclarés sans dispositif ou caducs avant séance |
| `COMPLETER` | 33 | 9.7 % | Adjonction in fine à la fin d'un article ou alinéa (priorité 800) |
| `REDIGER_AINSI` | 19 | 5.6 % | Réécriture intégrale d'un article ou alinéa (priorité 20) |
| `RETABLIR` | 4 | 1.2 % | Rétablissement d'un article ou d'une division supprimée |
| `AJOUTER` | 4 | 1.2 % | Insertion en tête d'article ou d'alinéa (« Au début ») |
| `REMPLACER` | 1 | 0.3 % | Remplacement d'un alinéa ou d'une division |

---

## Section 2 : Top des alertes de recevabilité et constitutionnelles

### 1. Alertes Article 40 de la Constitution (Diminution de recettes sans gage financier)

Ces amendements introduisent des dispositions à impact financier direct (exonération, compensation, crédit d'impôt) sans inclure de formule de gage constitutionnelle valide en fin de dispositif :

| N° | Auteur | Groupe | Risque et Motif d'irrecevabilité financière |
| :--- | :--- | :---: | :--- |
| **CD18** | Denis Fégné | SOC | Risque d'irrecevabilité financière au titre de l'Article 40 de la Constitution : diminution de ressources publiques ou création de charge détectée (« compensation ») sans formule de gage constitutionnel valide en fin de dispositif. |
| **CD21** | Denis Fégné | SOC | Risque d'irrecevabilité financière au titre de l'Article 40 de la Constitution : diminution de ressources publiques ou création de charge détectée (« compensation ») sans formule de gage constitutionnel valide en fin de dispositif. |
| **CF5** | Jean-Claude Raux | EcoS | Risque d'irrecevabilité financière au titre de l'Article 40 de la Constitution : diminution de ressources publiques ou création de charge détectée (« exonération ») sans formule de gage constitutionnel valide en fin de dispositif. |

### 2. Alertes Dispositions Non Normatives (Neutrons législatifs - Art. 6 DDHC)

Ces amendements comportent des formules déclaratives sans portée prescriptive réelle, passibles de censure par le Conseil constitutionnel (Décisions n° 2004-500 DC et 2005-512 DC) :

| N° | Auteur | Groupe | Extrait non normatif relevé |
| :--- | :--- | :---: | :--- |
| **CE23** | Romain Daubié | Dem | Formule détectée : `a vocation à`<br>« Rédiger ainsi cet article : « L’autorité compétente pour délivrer l’autorisation d’urbanisme peut proroger, au plus tard jusqu’au 31 juin 2032, le délai d’enlèvement d’une construction autorisée avant l’entrée en vigueur de la présente loi en application de l’article L. 433-1 du code de l’urbanisme lorsque cette construction a vocation à contrib... » |
| **AC145** | Romain Daubié | Dem | Formule détectée : `a vocation à`<br>« Rédiger ainsi cet article : « L’autorité compétente pour délivrer l’autorisation d’urbanisme peut proroger, au plus tard jusqu’au 31 juin 2032, le délai d’enlèvement d’une construction autorisée avant l’entrée en vigueur de la présente loi en application de l’article L. 433-1 du code de l’urbanisme lorsque cette construction a vocation à contrib... » |

---

## Section 3 : Journal exhaustif de qualification (1 ligne par amendement)

Format condensé strict d'une seule ligne par amendement :

| N° | Auteur (Groupe) | Article visé | Action & Cible | Rang Dérouleur | Art. 40 | Portée normative |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| AC137 | J. Bruneau (LIOT) | 5 | RETABLIR (Article entier) | 20 | Conforme | Normatif |
| AC52 | J.-C. Raux (EcoS) | 5 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC140 | B. Sorre (EPR) | 11 | SUPPRIMER (Alinéa 1, phrase 9) | 49 | Conforme | Normatif |
| AC15 | B. Sorre (EPR) | 11 | SUPPRIMER (Alinéas 12 à 13) | 150 | Conforme | Normatif |
| AC67 | J.-F. Coulomme (LFI-NFP) | AVANT PREMIER | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| AC69 | J.-F. Coulomme (LFI-NFP) | AVANT PREMIER | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| AC60 | J.-F. Coulomme (LFI-NFP) | PREMIER | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC64 | É. Martin (LFI-NFP) | PREMIER | COMPLETER (Alinéa 1, phrase 1) | 800 | Conforme | Normatif |
| AC71 | J.-F. Coulomme (LFI-NFP) | PREMIER | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC62 | J.-F. Coulomme (LFI-NFP) | PREMIER | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| AC65 | É. Martin (LFI-NFP) | PREMIER | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| AC61 | É. Martin (LFI-NFP) | APRÈS PREMIER | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC24 | C. Proença (SOC) | 2 | SUBSTITUER (Alinéas 3 à 5) | 60 | Conforme | Normatif |
| AC54 | J.-C. Raux (EcoS) | 3 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC78 | J.-F. Coulomme (LFI-NFP) | 3 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC128 | É. Martin (LFI-NFP) | 3 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC81 | J.-F. Coulomme (LFI-NFP) | 3 | INSERER (Mots) | 31 | Conforme | Normatif |
| AC18 | C. Proença (SOC) | 3 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| AC19 | C. Proença (SOC) | 3 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| AC21 | C. Proença (SOC) | 3 | INSERER (Mots) | 40 | Conforme | Normatif |
| AC129 | É. Martin (LFI-NFP) | 3 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC31 | C. Proença (SOC) | 3 | SUBSTITUER (Alinéa 14, mots) | 172 | Conforme | Normatif |
| AC20 | C. Proença (SOC) | 3 | SUBSTITUER (Mots) | 42 | Conforme | Normatif |
| AC130 | É. Martin (LFI-NFP) | 3 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC80 | É. Martin (LFI-NFP) | 3 | SUBSTITUER (Mots) | 30 | Conforme | Normatif |
| AC82 | É. Martin (LFI-NFP) | 3 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC86 | É. Martin (LFI-NFP) | 3 | SUPPRIMER (Alinéas 9 à 13) | 120 | Conforme | Normatif |
| AC133 | J.-F. Coulomme (LFI-NFP) | 3 | SUPPRIMER (Alinéas 9 à 10) | 120 | Conforme | Normatif |
| AC87 | J.-F. Coulomme (LFI-NFP) | 3 | SUPPRIMER (Alinéa) | 40 | Conforme | Normatif |
| AC84 | J.-F. Coulomme (LFI-NFP) | 3 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| AC88 | É. Martin (LFI-NFP) | 3 | SUPPRIMER (Alinéas 15 à 17) | 180 | Conforme | Normatif |
| AC131 | É. Martin (LFI-NFP) | 3 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC22 | C. Proença (SOC) | 3 | SUBSTITUER (Mots) | 32 | Conforme | Normatif |
| AC23 (Rect) | C. Proença (SOC) | 3 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC132 | É. Martin (LFI-NFP) | 3 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC55 | J.-C. Raux (EcoS) | 3 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| AC58 | J.-C. Raux (EcoS) | APRÈS 3 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CD50 | A. Jolly (RN) | 3 BIS | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CD18 | D. Fégné (SOC) | 3 BIS | REDIGER_AINSI (Article entier) | 20 | Alerte (sans gage) | Normatif |
| CD74 | M. Pochon (EcoS) | 3 BIS | INSERER (Alinéas 7 à 7) | 100 | Conforme | Normatif |
| CD19 | D. Fégné (SOC) | 3 BIS | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CD20 | D. Fégné (SOC) | 3 BIS | INSERER (Mots) | 40 | Conforme | Normatif |
| CD60 | O. Givernet (EPR) | 3 BIS | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CD32 | M. Pochon (EcoS) | 3 BIS | INSERER (Mots) | 40 | Conforme | Normatif |
| CD16 | J.-F. Coulomme (LFI-NFP) | 3 BIS | COMPLETER (Alinéa 1, phrase 1) | 40 | Conforme | Normatif |
| CD46 | É. Martin (LFI-NFP) | 3 BIS | COMPLETER (Alinéa 1, phrase 1) | 40 | Conforme | Normatif |
| CD33 | M. Pochon (EcoS) | 3 BIS | COMPLETER (Alinéa 1, phrase 1) | 40 | Conforme | Normatif |
| CD47 | J.-F. Coulomme (LFI-NFP) | 3 BIS | COMPLETER (Alinéa 1, phrase 1) | 40 | Conforme | Normatif |
| CD21 | D. Fégné (SOC) | 3 BIS | INSERER (Alinéa) | 40 | Alerte (sans gage) | Normatif |
| CD61 | O. Givernet (EPR) | 3 BIS | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CD34 | M. Pochon (EcoS) | 3 BIS | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| CD22 | D. Fégné (SOC) | APRÈS 3 BIS | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| CD67 | M. Pochon (EcoS) | APRÈS 3 BIS | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| CD69 | J. Lechanteux (RN) | APRÈS 3 BIS | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC102 | J.-F. Coulomme (LFI-NFP) | 4 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC103 | J.-F. Coulomme (LFI-NFP) | 4 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| AC136 | J. Bruneau (LIOT) | APRÈS 4 | INSERER (Article additionnel) | 900 | Conforme (Gage Tabac (État)) | Normatif |
| AC37 | C. Rouaux (SOC) | APRÈS 5 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| AC76 | J.-F. Coulomme (LFI-NFP) | APRÈS 5 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC1 | F. Maillot (GDR) | APRÈS 5 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC47 | C. Proença (SOC) | APRÈS 5 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC45 | C. Rouaux (SOC) | APRÈS 5 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC63 | É. Martin (LFI-NFP) | APRÈS 5 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC32 | C. Proença (SOC) | 6 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| AC33 | C. Proença (SOC) | 6 | SUPPRIMER (Mots) | 41 | Conforme | Normatif |
| AC16 | C. Proença (SOC) | 6 | INSERER (Mots) | 42 | Conforme | Normatif |
| AC34 | C. Proença (SOC) | 6 | REDIGER_AINSI (Alinéa 1, phrase 2) | 42 | Conforme | Normatif |
| AC44 | C. Rouaux (SOC) | 6 | INSERER (Mots) | 40 | Conforme | Normatif |
| AC25 | G. Bannier (Dem) | 6 | REDIGER_AINSI (Alinéa 1, phrase 2) | 42 | Conforme | Normatif |
| AC105 | É. Martin (LFI-NFP) | 6 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC48 | S. Viry (LIOT) | APRÈS 6 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| AC17 | C. Proença (SOC) | 7 | RETABLIR (Division) | 40 | Conforme | Normatif |
| AC46 | C. Rouaux (SOC) | 7 | RETABLIR (Division) | 40 | Conforme | Normatif |
| AC134 | J.-C. Raux (EcoS) | 7 | RETABLIR (Division) | 40 | Conforme | Normatif |
| AC53 | J.-C. Raux (EcoS) | 7 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| AC59 | S. Bourouaha (GDR) | 7 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| AC135 | J.-F. Coulomme (LFI-NFP) | 7 | SUPPRIMER (Mots) | 41 | Conforme | Normatif |
| AC111 | É. Martin (LFI-NFP) | 7 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| AC141 | C. Proença (SOC) | 7 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| AC113 | J.-F. Coulomme (LFI-NFP) | 7 | COMPLETER (Alinéa) | 40 | Conforme | Normatif |
| AC109 | É. Martin (LFI-NFP) | 7 | COMPLETER (Alinéas 2 à 2) | 50 | Conforme | Normatif |
| AC49 | S. Bourouaha (GDR) | 7 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC50 | S. Bourouaha (GDR) | APRÈS 7 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| CF2 | B. Dirx (EPR) | 8 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| CF1 | J.-C. Raux (EcoS) | 8 | SUPPRIMER (Mots) | 41 | Conforme | Normatif |
| CF3 | B. Dirx (EPR) | 8 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CF5 | J.-C. Raux (EcoS) | APRÈS 8 | INSERER (Article additionnel) | 900 | Alerte (sans gage) | Normatif |
| CF4 | J.-C. Raux (EcoS) | APRÈS 8 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC115 | J.-F. Coulomme (LFI-NFP) | 9 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| AC114 | J.-F. Coulomme (LFI-NFP) | 9 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| AC116 | É. Martin (LFI-NFP) | 9 BIS | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| AC117 | J.-F. Coulomme (LFI-NFP) | 10 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC108 | J.-F. Coulomme (LFI-NFP) | APRÈS 10 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| AC112 | É. Martin (LFI-NFP) | APRÈS 10 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC2 | C. Proença (SOC) | APRÈS 11 | COMPLETER (Article additionnel) | 900 | Conforme | Normatif |
| AC35 | B. Belhaddad (SOC) | APRÈS 11 | COMPLETER (Article additionnel) | 900 | Conforme | Normatif |
| CD7 | J.-F. Coulomme (LFI-NFP) | 12 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CD35 | M. Pochon (EcoS) | 12 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CD24 | D. Fégné (SOC) | 12 | REDIGER_AINSI (Article entier) | 20 | Conforme | Normatif |
| CD25 | D. Fégné (SOC) | 12 | INSERER (Mots) | 40 | Conforme | Normatif |
| CD3 | X. Roseren (HOR) | 12 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CD36 | M. Pochon (EcoS) | 12 | SUBSTITUER (Alinéa 2, mots) | 50 | Conforme | Normatif |
| CD8 | É. Martin (LFI-NFP) | 12 | SUBSTITUER (Alinéa 2, mots) | 50 | Conforme | Normatif |
| CD26 | D. Fégné (SOC) | 12 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CD39 | M. Pochon (EcoS) | 12 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CD38 | M. Pochon (EcoS) | 12 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| CD62 | O. Givernet (EPR) | 12 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| CD63 | O. Givernet (EPR) | 12 | INSERER (Mots) | 40 | Conforme | Normatif |
| CD11 | J.-F. Coulomme (LFI-NFP) | 12 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CD9 | J.-F. Coulomme (LFI-NFP) | 12 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CD37 | M. Pochon (EcoS) | 12 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CD23 | D. Fégné (SOC) | APRÈS 12 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| CD51 | A. Jolly (RN) | APRÈS 12 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CD72 | R. Daubié (Dem) | APRÈS 12 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CD73 | R. Daubié (Dem) | APRÈS 12 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CD4 | F. Brun (DR) | APRÈS 12 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CD10 | É. Martin (LFI-NFP) | APRÈS 12 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| CE1 | É. Martin (LFI-NFP) | 13 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CE9 | J.-C. Raux (EcoS) | 13 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CE10 | J.-C. Raux (EcoS) | 13 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| CE14 | V. Rossi (SOC) | 13 | REMPLACER (Mots) | 40 | Conforme | Normatif |
| CE15 | V. Rossi (SOC) | 13 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CE21 | R. Daubié (Dem) | 13 | SUBSTITUER (Mots) | 49 | Conforme | Normatif |
| CE11 | J.-C. Raux (EcoS) | 14 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CE2 | J.-F. Coulomme (LFI-NFP) | 14 | SUPPRIMER (Alinéas 2 à 3) | 50 | Conforme | Normatif |
| AC51 | J.-C. Raux (EcoS) | 15 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC104 | É. Martin (LFI-NFP) | 15 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC3 | B. Sorre (EPR) | 15 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC106 | J.-F. Coulomme (LFI-NFP) | 16 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC5 | B. Sorre (EPR) | 16 | INSERER (Mots) | 40 | Conforme | Normatif |
| AC27 | B. Sorre (EPR) | 16 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC4 | B. Sorre (EPR) | 16 | INSERER (Mots) | 40 | Conforme | Normatif |
| AC28 | B. Sorre (EPR) | 16 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| CE12 | J.-C. Raux (EcoS) | 17 | SUPPRIMER (Alinéa 1, phrase 2) | 42 | Conforme | Normatif |
| CE22 | R. Daubié (Dem) | 17 | SUPPRIMER (Mots) | 41 | Conforme | Normatif |
| CE3 | É. Martin (LFI-NFP) | 17 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CE13 | J.-C. Raux (EcoS) | 17 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CE4 | J.-F. Coulomme (LFI-NFP) | 18 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CE23 | R. Daubié (Dem) | 18 | REDIGER_AINSI (Article entier) | 20 | Conforme | Alerte (non normatif) |
| CD12 | J.-F. Coulomme (LFI-NFP) | 18 BIS | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CD27 | D. Fégné (SOC) | 18 BIS | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CD40 | M. Pochon (EcoS) | 18 BIS | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CD68 | O. Givernet (EPR) | 18 BIS | REDIGER_AINSI (Article entier) | 20 | Conforme | Normatif |
| CD52 | J. Bruneau (LIOT) | 18 BIS | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| CD48 | A. Jolly (RN) | APRÈS 18 BIS | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| CE5 | É. Martin (LFI-NFP) | 19 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CE8 | J.-C. Raux (EcoS) | 19 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CE24 | R. Daubié (Dem) | 19 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| CE27 | R. Daubié (Dem) | 20 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CE6 | J.-F. Coulomme (LFI-NFP) | 20 | COMPLETER (Mots) | 41 | Conforme | Normatif |
| CE28 | R. Daubié (Dem) | 20 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CE25 | R. Daubié (Dem) | 20 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| CE16 | V. Rossi (SOC) | 20 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CD28 | D. Fégné (SOC) | 21 | REDIGER_AINSI (Article entier) | 20 | Conforme | Normatif |
| CD75 | M. Pochon (EcoS) | 21 | INSERER (Mots) | 40 | Conforme | Normatif |
| CD70 | J. Lechanteux (RN) | 21 | INSERER (Mots) | 40 | Conforme | Normatif |
| CD49 | A. Jolly (RN) | 21 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| CD13 | J.-F. Coulomme (LFI-NFP) | 21 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| CD29 | D. Fégné (SOC) | 21 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| CD5 | X. Roseren (HOR) | 21 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| CD6 | X. Roseren (HOR) | 21 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| CD2 | X. Roseren (HOR) | 21 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| CD41 | M. Pochon (EcoS) | 21 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| CD43 | M. Pochon (EcoS) | APRÈS 21 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| CD42 | M. Pochon (EcoS) | APRÈS 21 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| CD14 | É. Martin (LFI-NFP) | 22 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CD54 | O. Givernet (EPR) | 22 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| CD55 | O. Givernet (EPR) | 22 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| CD30 | D. Fégné (SOC) | 22 | INSERER (Mots) | 40 | Conforme | Normatif |
| CD56 | O. Givernet (EPR) | 22 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CD71 | J. Lechanteux (RN) | 22 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CD31 | D. Fégné (SOC) | 22 | COMPLETER (Mots) | 40 | Conforme | Normatif |
| CD57 | O. Givernet (EPR) | 22 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CD58 | O. Givernet (EPR) | 22 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CD59 | O. Givernet (EPR) | 22 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| CD15 | J.-F. Coulomme (LFI-NFP) | 22 | SUPPRIMER (Alinéa) | 40 | Conforme | Normatif |
| CD17 | P. Meurin (RN) | 22 | SUPPRIMER (Alinéa) | 40 | Conforme | Normatif |
| CD44 | M. Pochon (EcoS) | 22 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CD45 | S. Peytavie (EcoS) | APRÈS 22 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| CE19 | V. Rolland (DR) | 24 | REDIGER_AINSI (Alinéas 3 à 3) | 60 | Conforme | Normatif |
| CE20 | V. Rolland (DR) | 24 | REDIGER_AINSI (Alinéa) | 40 | Conforme | Normatif |
| CE26 | R. Daubié (Dem) | 24 | INSERER (Alinéas 3 à 3) | 60 | Conforme | Normatif |
| CE7 | É. Martin (LFI-NFP) | 24 | INSERER (Alinéa 1, phrase 1) | 41 | Conforme | Normatif |
| AC6 | PA795278 (HOR) | 25 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC120 | J.-F. Coulomme (LFI-NFP) | 25 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| AC57 | J.-C. Raux (EcoS) | APRÈS 25 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC73 | J.-F. Coulomme (LFI-NFP) | APRÈS 25 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC74 | É. Martin (LFI-NFP) | APRÈS 25 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC7 | PA795278 (HOR) | 26 | INSERER (Mots) | 40 | Conforme | Normatif |
| AC8 | PA795278 (HOR) | 27 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC9 | C. Proença (SOC) | 27 BIS | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC36 | B. Belhaddad (SOC) | 27 BIS | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC121 | J.-F. Coulomme (LFI-NFP) | 27 BIS | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC123 | F. Maillot (GDR) | 27 BIS | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC10 | C. Proença (SOC) | 27 TER | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC91 | É. Martin (LFI-NFP) | 28 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC92 | É. Martin (LFI-NFP) | 28 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC93 | É. Martin (LFI-NFP) | 28 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC94 | É. Martin (LFI-NFP) | 28 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC95 | É. Martin (LFI-NFP) | 28 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC96 | É. Martin (LFI-NFP) | 28 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC97 | É. Martin (LFI-NFP) | 28 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC98 | É. Martin (LFI-NFP) | 28 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC99 | É. Martin (LFI-NFP) | 28 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC100 | É. Martin (LFI-NFP) | 28 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC107 | É. Martin (LFI-NFP) | 28 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC11 | PA795278 (HOR) | 28 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| AC110 | É. Martin (LFI-NFP) | 28 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC29 | PA795278 (HOR) | 28 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| AC30 | PA795278 (HOR) | 28 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| AC12 | PA795278 (HOR) | 28 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| AC118 | É. Martin (LFI-NFP) | 28 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC13 | PA795278 (HOR) | 28 | INSERER (Mots) | 40 | Conforme | Normatif |
| AC119 | J.-F. Coulomme (LFI-NFP) | APRÈS 28 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC14 | PA795278 (HOR) | 29 | COMPLETER (Mots) | 41 | Conforme | Normatif |
| AC85 | J.-F. Coulomme (LFI-NFP) | 30 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC124 | S. Bourouaha (GDR) | 30 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC75 | É. Martin (LFI-NFP) | 30 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC83 | É. Martin (LFI-NFP) | 30 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| AC40 | P. Courbon (SOC) | 30 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| AC125 | F. Maillot (GDR) | 30 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| AC41 | P. Courbon (SOC) | 30 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC42 | P. Courbon (SOC) | 30 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC56 | J.-C. Raux (EcoS) | 30 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC38 | P. Courbon (SOC) | 30 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC43 | P. Courbon (SOC) | 30 | INSERER (Mots) | 40 | Conforme | Normatif |
| AC126 | F. Maillot (GDR) | 30 | INSERER (Mots) | 40 | Conforme | Normatif |
| AC39 | P. Courbon (SOC) | 30 | COMPLETER (Alinéa 1, phrase 1) | 40 | Conforme | Normatif |
| AC68 | J.-F. Coulomme (LFI-NFP) | 30 | INSERER (Alinéa 1, phrase 2) | 42 | Conforme | Normatif |
| AC79 | É. Martin (LFI-NFP) | 30 | SUPPRIMER (Alinéa) | 40 | Conforme | Normatif |
| AC72 | É. Martin (LFI-NFP) | 30 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| AC77 | É. Martin (LFI-NFP) | 30 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC70 | É. Martin (LFI-NFP) | APRÈS 30 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC66 | É. Martin (LFI-NFP) | APRÈS 30 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CL8 | S. Regol (EcoS) | 31 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL39 | É. Martin (LFI-NFP) | 31 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL40 | E. Faucillon (GDR) | 31 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL12 | S. Regol (EcoS) | 31 | AJOUTER (Mots) | 31 | Conforme | Normatif |
| CL4 | M.-J. Allemand (SOC) | 31 | AJOUTER (Mots) | 31 | Conforme | Normatif |
| CL2 | V. Riotton (EPR) | 31 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| CL9 | S. Regol (EcoS) | 31 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| CL57 | P. Molac (LIOT) | 31 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| CL48 | É. Bonnivard (DR) | 31 | INSERER (Mots) | 41 | Conforme | Normatif |
| CL10 | S. Regol (EcoS) | 31 | SUBSTITUER (Mots) | 42 | Conforme | Normatif |
| CL38 | J.-F. Coulomme (LFI-NFP) | 31 | COMPLETER (Mots) | 42 | Conforme | Normatif |
| CL11 | S. Regol (EcoS) | 31 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| CL23 | S. Regol (EcoS) | 31 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| CL13 | S. Regol (EcoS) | APRÈS 31 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CL58 | J. Rancoule (RN) | APRÈS 31 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CL36 | É. Martin (LFI-NFP) | 32 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL49 | É. Bonnivard (DR) | 32 | SUBSTITUER (Alinéa) | 40 | Conforme | Normatif |
| CL5 | M.-J. Allemand (SOC) | 32 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| CL35 | É. Martin (LFI-NFP) | 33 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL59 | J. Rancoule (RN) | 33 | AJOUTER (Alinéa) | 30 | Conforme | Normatif |
| CL34 | É. Martin (LFI-NFP) | 33 | COMPLETER (Article in fine) | 800 | Conforme | Normatif |
| CL6 | M.-J. Allemand (SOC) | 34 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL33 | É. Martin (LFI-NFP) | 34 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL41 | E. Faucillon (GDR) | 34 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL61 | P. Amirshahi (EcoS) | 34 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL16 | S. Regol (EcoS) | 34 | INSERER (Mots) | 40 | Conforme | Normatif |
| CL32 | É. Martin (LFI-NFP) | 34 | SUBSTITUER (Mots) | 39 | Conforme | Normatif |
| CL15 | S. Regol (EcoS) | 34 | SUBSTITUER (Mots) | 49 | Conforme | Normatif |
| CL14 | S. Regol (EcoS) | 34 | SUPPRIMER (Alinéa) | 40 | Conforme | Normatif |
| CL17 | S. Regol (EcoS) | 34 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CL30 | É. Martin (LFI-NFP) | 34 | SUPPRIMER (Alinéa) | 40 | Conforme | Normatif |
| CL29 | J.-F. Coulomme (LFI-NFP) | APRÈS 34 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CL27 | É. Martin (LFI-NFP) | APRÈS 34 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CL31 | J.-F. Coulomme (LFI-NFP) | APRÈS 34 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CL7 | M.-J. Allemand (SOC) | 35 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL18 | S. Regol (EcoS) | 35 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL22 | P. Molac (LIOT) | 35 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL42 | É. K/Bidi (GDR) | 35 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL50 | É. Martin (LFI-NFP) | 35 | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| CL51 | J.-F. Coulomme (LFI-NFP) | 35 | REDIGER_AINSI (Article entier) | 20 | Conforme | Normatif |
| CL52 | J.-F. Coulomme (LFI-NFP) | 35 | REDIGER_AINSI (Article entier) | 20 | Conforme | Normatif |
| CL24 | É. Martin (LFI-NFP) | 35 | REDIGER_AINSI (Article entier) | 20 | Conforme | Normatif |
| CL3 | M.-J. Allemand (SOC) | 35 | REDIGER_AINSI (Article entier) | 20 | Conforme | Normatif |
| CL53 | J.-F. Coulomme (LFI-NFP) | 35 | REDIGER_AINSI (Article entier) | 20 | Conforme | Normatif |
| CL44 | J. Guitton (RN) | 35 | REDIGER_AINSI (Alinéa) | 40 | Conforme | Normatif |
| CL25 | É. Martin (LFI-NFP) | 35 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| CL21 | S. Regol (EcoS) | 35 | REDIGER_AINSI (Alinéa) | 40 | Conforme | Normatif |
| CL45 | J. Guitton (RN) | 35 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CL46 | J. Guitton (RN) | 35 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CL26 | É. Martin (LFI-NFP) | 35 | SUPPRIMER (Alinéa) | 40 | Conforme | Normatif |
| CL19 | S. Regol (EcoS) | 35 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CL20 | S. Regol (EcoS) | 35 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CL54 | É. Martin (LFI-NFP) | 35 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CL47 | J. Guitton (RN) | 35 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| CL55 | É. Martin (LFI-NFP) | APRÈS 35 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CL28 | É. Martin (LFI-NFP) | APRÈS 35 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| CL37 | É. Martin (LFI-NFP) | APRÈS 35 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| CL56 | É. Martin (LFI-NFP) | APRÈS 35 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC139 | J. Bruneau (LIOT) | APRÈS 35 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CL60 | J. Rancoule (RN) | APRÈS 35 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| CD64 | O. Givernet (EPR) | 36 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| CD66 | O. Givernet (EPR) | 36 | SUBSTITUER (Alinéa) | 40 | Conforme | Normatif |
| CD65 | O. Givernet (EPR) | 36 | INSERER (Mots) | 40 | Conforme | Normatif |
| AC90 | É. Martin (LFI-NFP) | 3 BIS | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC101 | J.-F. Coulomme (LFI-NFP) | 3 BIS | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC155 | O. Givernet (EPR) | 3 BIS | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC156 | O. Givernet (EPR) | 3 BIS | INSERER (Mots) | 40 | Conforme | Normatif |
| AC157 | O. Givernet (EPR) | 3 BIS | COMPLETER (Alinéa 1, phrase 1) | 40 | Conforme | Normatif |
| AC158 | O. Givernet (EPR) | 3 BIS | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC180 | B. Dirx (EPR) | 8 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC179 | B. Dirx (EPR) | APRÈS 8 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC159 | O. Givernet (EPR) | 12 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC160 | O. Givernet (EPR) | 12 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| AC161 | O. Givernet (EPR) | 12 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| AC162 | O. Givernet (EPR) | 12 | INSERER (Mots) | 40 | Conforme | Normatif |
| AC26 | G. Bannier (Dem) | 13 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC143 | R. Daubié (Dem) | 13 | SUBSTITUER (Mots) | 49 | Conforme | Normatif |
| AC144 | R. Daubié (Dem) | 17 | SUPPRIMER (Mots) | 41 | Conforme | Normatif |
| AC145 | R. Daubié (Dem) | 18 | REDIGER_AINSI (Article entier) | 20 | Conforme | Alerte (non normatif) |
| AC163 | O. Givernet (EPR) | 18 BIS | SUPPRIMER (Article entier) | 10 | Conforme | Normatif |
| AC138 | J. Bruneau (LIOT) | 18 BIS | AJOUTER (Article) | 40 | Conforme | Normatif |
| AC146 | R. Daubié (Dem) | 19 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| AC149 | R. Daubié (Dem) | 20 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC150 | R. Daubié (Dem) | 20 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC147 | R. Daubié (Dem) | 20 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| AC164 | O. Givernet (EPR) | 21 | REDIGER_AINSI (Article entier) | 20 | Conforme | Normatif |
| AC165 | O. Givernet (EPR) | APRÈS 21 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC166 | O. Givernet (EPR) | 22 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| AC167 | O. Givernet (EPR) | 22 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| AC168 | O. Givernet (EPR) | 22 | INSERER (Mots) | 40 | Conforme | Normatif |
| AC169 | O. Givernet (EPR) | 22 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC171 | O. Givernet (EPR) | 22 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC172 | O. Givernet (EPR) | 22 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC173 | O. Givernet (EPR) | 22 | SUPPRIMER (Mots) | 40 | Conforme | Normatif |
| AC174 | O. Givernet (EPR) | 22 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| AC127 | S. Peytavie (EcoS) | APRÈS 22 | Sans dispositif (Retiré/Caduc) | 900 | Conforme | Normatif |
| AC175 | O. Givernet (EPR) | APRÈS 22 | INSERER (Article additionnel) | 900 | Conforme | Normatif |
| AC142 | R. Daubié (Dem) | 24 | REDIGER_AINSI (Alinéa) | 40 | Conforme | Normatif |
| AC148 | R. Daubié (Dem) | 24 | INSERER (Alinéas 3 à 3) | 60 | Conforme | Normatif |
| AC152 | V. Riotton (EPR) | 31 | SUBSTITUER (Mots) | 41 | Conforme | Normatif |
| AC153 | V. Riotton (EPR) | 31 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC151 | V. Riotton (EPR) | 31 | Sans dispositif (Retiré/Caduc) | 40 | Conforme | Normatif |
| AC154 | V. Riotton (EPR) | 31 | SUBSTITUER (Mots) | 42 | Conforme | Normatif |
| AC170 | V. Riotton (EPR) | 35 | INSERER (Alinéa) | 40 | Conforme | Normatif |
| AC176 | O. Givernet (EPR) | 36 | SUBSTITUER (Mots) | 40 | Conforme | Normatif |
| AC177 | O. Givernet (EPR) | 36 | SUBSTITUER (Alinéa) | 40 | Conforme | Normatif |
| AC178 | O. Givernet (EPR) | 36 | INSERER (Mots) | 40 | Conforme | Normatif |
