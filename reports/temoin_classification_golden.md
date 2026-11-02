# Golden Dataset Sémantique de Référence — Vérité Terrain (341 Amendements)

> **Bourbon.ia — Moteur de Benchmark de Référence (Oracle Sémantique)**  
> *Source : `public/sample-amendments.json` | Corpus qualifié : 341 amendements | Règlements AN & Sénat*

---

## Section 1 : Bilan consolidé de la vérité terrain

| Statut Témoin | Effectif (Amendements) | Part relative | Rôle dans l'évaluation sémantique |
| :--- | :---: | :---: | :--- |
| **Identique** | **120** | 35.2 % | Détection mécanique stricte par empreinte et même article (coût LLM 0) |
| **Discussion commune** | **122** | 35.8 % | Conflits de fond arbitrés par l'IA (grappes concurrentes réelles) |
| **Isolé** | **99** | 29.0 % | Sans dispositif (45 ams), divisions uniques ou dispositions spécifiques |
| **TOTAL GÉNÉRAL** | **341** | **100,0 %** | **Vérification intégrale des 341 amendements du corpus** |

---

## Section 2 : Focus sur les grappes de discussion commune (Conflits parlementaires par article)

Les articles suivants concentrent les principales oppositions politiques et techniques en séance :

### Article 3 (16 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **AC128** | Élisa Martin (LFI-NFP) | `AC81` | Concurrence directe sur les délais dérogatoires de publicité à l'alinéa 1er. |
| **AC81** | Jean-François Coulomme (LFI-NFP) | `AC128` | Concurrence directe sur la date d'entrée en vigueur de la dérogation publicitaire à l'alinéa 1er. |
| **AC19** | Christophe Proença (SOC) | `AC129` | Concurrence sur le champ des dérogations d'affichage et de publicité à l'alinéa 5. |
| **AC21** | Christophe Proença (SOC) | `AC129` | Précision temporelle sur l'affichage à l'alinéa 5 en concurrence avec la substitution globale de AC129. |
| **AC129** | Élisa Martin (LFI-NFP) | `AC19` | Substitution du calendrier d'affichage à l'alinéa 5 en concurrence avec la suppression de AC19. |
| **AC31** | Christophe Proença (SOC) | `AC20` | Concurrence rédactionnelle sur l'encadrement des nuisances à la seconde phrase de l'alinéa 6 (optimiser vs limiter). |
| **AC20** | Christophe Proença (SOC) | `AC31` | Concurrence rédactionnelle sur la qualification des impacts/nuisances à la seconde phrase de l'alinéa 6. |
| **AC80** | Élisa Martin (LFI-NFP) | `AC82` | Concurrence sur la période temporelle des dérogations publicitaires autour des sites à l'alinéa 8. |
| **AC82** | Élisa Martin (LFI-NFP) | `AC80` | Concurrence sur le rayon kilométrique de restriction publicitaire à l'alinéa 8 (500m vs 200m). |
| **AC86** | Élisa Martin (LFI-NFP) | `AC82` | Suppression de la seconde moitié de l'alinéa 8 en concurrence avec les seuils kilométriques de AC82. |
| **AC88** | Élisa Martin (LFI-NFP) | `AC131` | Suppression globale des alinéas 15 à 17 en conflit direct avec les modifications d'alinéa de AC131 et AC22. |
| **AC131** | Élisa Martin (LFI-NFP) | `AC22` | Concurrence directe sur les dates limites de la dérogation publicitaire à l'alinéa 16. |
| **AC22** | Christophe Proença (SOC) | `AC131` | Concurrence rédactionnelle sur les affichages autorisés à la 2de phrase de l'alinéa 16. |
| **AC23 (Rect)** | Christophe Proença (SOC) | `AC132` | Concurrence directe sur les dérogations publicitaires et dates d'application de l'alinéa 18. |
| **AC132** | Élisa Martin (LFI-NFP) | `AC23 (Rect)` | Concurrence directe sur le calendrier d'interdiction publicitaire à l'alinéa 18. |
| **AC55** | Jean-Claude Raux (EcoS) | `AC132` | Insertion d'un alinéa d'interdiction après l'alinéa 18 en concurrence avec le régime dérogatoire de AC132. |

### Article 35 (13 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CL51** | Jean-François Coulomme (LFI-NFP) | `CL52` | Abrogation totale de l'article 10 de la loi JO 2024 en concurrence avec les réécritures partielles de CL52 et CL3. |
| **CL52** | Jean-François Coulomme (LFI-NFP) | `CL51` | Interdiction de la biométrie et reconnaissance faciale en concurrence avec l'abrogation de CL51. |
| **CL24** | Élisa Martin (LFI-NFP) | `CL3` | Interdiction de prolongation de la VSA au-delà de 2026 en concurrence avec l'expérimentation de CL3. |
| **CL3** | Marie-José Allemand (SOC) | `CL51` | Limitation de l'expérimentation VSA à la seule durée des Jeux 2030 en concurrence avec CL51 et CL24. |
| **CL53** | Jean-François Coulomme (LFI-NFP) | `CL3` | Encadrement des finalités de sécurité de la VSA en concurrence avec les régimes dérogatoires alternatifs. |
| **CL44** | Jordan Guitton (RN) | `CL21` | Réécriture de l'alinéa 3 prolongeant la VSA jusqu'en 2027 en concurrence avec CL21 et CL45. |
| **CL21** | Sandra Regol (EcoS) | `CL44` | Réécriture alternative de l'alinéa 3 encadrant le rapport d'évaluation en concurrence avec CL44. |
| **CL45** | Jordan Guitton (RN) | `CL44` | Prolongation de l'expérimentation jusqu'au 31 décembre 2027 à l'alinéa 3 en concurrence avec CL44. |
| **CL46** | Jordan Guitton (RN) | `CL44` | Insertion d'un a bis prolongeant les algorithmes après l'alinéa 3 en concurrence avec CL44. |
| **CL26** | Élisa Martin (LFI-NFP) | `CL19` | Suppression de l'alinéa 4 en conflit direct avec les ajouts de garanties de CL19, CL54 et CL47. |
| **CL19** | Sandra Regol (EcoS) | `CL54` | Interdiction expresse de la reconnaissance vocale après l'alinéa 4 en concurrence avec CL54 et CL47. |
| **CL54** | Élisa Martin (LFI-NFP) | `CL19` | Exigence d'un arrêté préfectoral motivé après l'alinéa 4 en concurrence avec les garanties de CL19. |
| **CL47** | Jordan Guitton (RN) | `CL19` | Rapport annuel de la CNIL après l'alinéa 4 en concurrence avec les verrous de CL19 et CL54. |

### Article 3 BIS (8 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CD50** | Alexis Jolly (RN) | `CD18` | Suppression de l'article 3 BIS en concurrence frontale avec la réécriture globale de CD18. |
| **CD18** | Denis Fégné (SOC) | `CD68` | Réécriture globale concurrente de l'article 3 BIS en conflit direct avec la version de CD68. |
| **CD19** | Denis Fégné (SOC) | `CD60` | Concurrence sur le délai de remise du bilan environnemental à l'alinéa 1er (12 mois vs 24 mois). |
| **CD20** | Denis Fégné (SOC) | `CD32` | Concurrence sur les institutions associées au rapport (Haut Conseil pour le Climat) à l'alinéa 1er. |
| **CD46** | Élisa Martin (LFI-NFP) | `CD16` | Concurrence sur le contenu obligatoire du rapport environnemental à l'alinéa 1er. |
| **CD33** | Marie Pochon (EcoS) | `CD47` | Concurrence sur l'association des associations environnementales à l'alinéa 1er. |
| **CD47** | Jean-François Coulomme (LFI-NFP) | `CD33` | Concurrence sur la formulation de la contribution associative au bilan carbone à l'alinéa 1er. |
| **CD21** | Denis Fégné (SOC) | `CD18` | Insertion d'un I bis créant un mécanisme d'indemnisation financière en suite du rapport. |

### Article 7 (8 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **AC134** | Jean-Claude Raux (EcoS) | `AC17` | Rétablissement concurrent du paragraphe I sur la désignation des parlementaires au conseil d'administration. |
| **AC53** | Jean-Claude Raux (EcoS) | `AC59` | Insertion d'un I bis plafonnant les rémunérations des dirigeants en concurrence avec AC59. |
| **AC59** | Soumya Bourouaha (GDR) | `AC53` | Plafonnement des dix principales rémunérations à l'alinéa 1 bis en concurrence avec AC53. |
| **AC135** | Jean-François Coulomme (LFI-NFP) | `AC111` | Suppression du seuil restrictif de dix rémunérations en concurrence avec les seuils de AC111 et AC141. |
| **AC111** | Élisa Martin (LFI-NFP) | `AC141` | Extension de la transparence aux 100 premières rémunérations à l'alinéa 2 (vs 20 pour AC141). |
| **AC141** | Christophe Proença (SOC) | `AC111` | Extension de la transparence aux 20 premières rémunérations à l'alinéa 2 (vs 100 pour AC111). |
| **AC113** | Jean-François Coulomme (LFI-NFP) | `AC109` | Plan d'encadrement des écarts salariaux complétant l'alinéa 2 en concurrence avec le débat de AC109. |
| **AC109** | Élisa Martin (LFI-NFP) | `AC113` | Exigence d'un débat parlementaire complétant l'alinéa 2 en concurrence avec AC113. |

### Article 21 (8 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CD75** | Marie Pochon (EcoS) | `CD28` | Garantie environnementale à l'alinéa 4 en concurrence avec la réécriture globale de CD28. |
| **CD70** | Julie Lechanteux (RN) | `CD28` | Renforcement de la sécurité physique des transports en concurrence avec la réécriture de CD28. |
| **CD49** | Alexis Jolly (RN) | `CD13` | Volet mobilités partagées complétant le rapport in fine en concurrence avec les propositions de CD13. |
| **CD13** | Jean-François Coulomme (LFI-NFP) | `CD49` | Volet pérennité des infrastructures complétant le rapport in fine en concurrence avec CD49 et CD29. |
| **CD29** | Denis Fégné (SOC) | `CD5` | Précision sur les liaisons ferroviaires complétant le rapport in fine en concurrence avec CD5. |
| **CD5** | Xavier Roseren (HOR) | `CD6` | Volet ferroviaire détaillé en 7 alinéas complétant le rapport in fine en concurrence avec CD6. |
| **CD6** | Xavier Roseren (HOR) | `CD5` | Sous-volet transports du quotidien complétant le rapport in fine en concurrence avec CD5. |
| **CD41** | Marie Pochon (EcoS) | `CD49` | Rattachement des projets d'intermodalité complétant le rapport in fine en concurrence avec CD49. |

### Article 30 (8 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **AC83** | Élisa Martin (LFI-NFP) | `AC41` | Suppression des communes limitrophes à l'alinéa 1er en concurrence avec le transfert au maire de AC41. |
| **AC41** | Pierrick Courbon (SOC) | `AC42` | Transfert de la décision dérogatoire au maire sur délibération à l'alinéa 1er (vs arrêté simple pour AC42). |
| **AC42** | Pierrick Courbon (SOC) | `AC41` | Transfert direct au maire de la dérogation dominicale à l'alinéa 1er en concurrence avec AC41. |
| **AC56** | Jean-Claude Raux (EcoS) | `AC38` | Restriction de la période de dérogation dominicale à l'alinéa 1er (février vs trimestre complet). |
| **AC38** | Pierrick Courbon (SOC) | `AC56` | Concurrence sur le calendrier strict de dérogation au repos dominical à l'alinéa 1er. |
| **AC43** | Pierrick Courbon (SOC) | `AC126` | Exigence d'un avis 'conforme' du maire à l'alinéa 2 en concurrence avec l'avis 'favorable' de AC126. |
| **AC126** | Frédéric Maillot (GDR) | `AC43` | Exigence d'un avis 'favorable' du maire à l'alinéa 2 en concurrence avec l'avis 'conforme' de AC43. |
| **AC39** | Pierrick Courbon (SOC) | `AC43` | Délai de prévenance de deux mois complétant l'alinéa 2 en concurrence avec les avis de AC43 et AC126. |

### Article 6 (6 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **AC32** | Christophe Proença (SOC) | `AC33` | Concurrence sur la qualification de l'approbation ministérielle à la 1re phrase de l'alinéa unique. |
| **AC33** | Christophe Proença (SOC) | `AC32` | Suppression de la mention des dispositions législatives à la 1re phrase de l'alinéa unique en concurrence avec AC32. |
| **AC16** | Christophe Proença (SOC) | `AC34` | Extension aux violences sexistes à la 2de phrase de l'alinéa unique en concurrence avec AC34 et AC25. |
| **AC34** | Christophe Proença (SOC) | `AC25` | Réécriture de la fin de la 2de phrase de l'alinéa unique en concurrence directe avec AC25. |
| **AC44** | Claudia Rouaux (SOC) | `AC25` | Insertion d'une obligation de formation aux discriminations en concurrence avec la rédaction de AC25. |
| **AC25** | Géraldine Bannier (Dem) | `AC34` | Réécriture concurrente de la fin de la 2de phrase de l'alinéa unique sur les discriminations. |

### Article 12 (6 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CD24** | Denis Fégné (SOC) | `CD36` | Réécriture globale du régime de participation du public en concurrence avec les réécritures partielles. |
| **CD25** | Denis Fégné (SOC) | `CD3` | Précision sur la démarche environnementale à l'alinéa 1er en concurrence avec le caractère facultatif de CD3. |
| **CD36** | Marie Pochon (EcoS) | `CD24` | Substitution de la base légale de consultation (L. 123-1) et suppression des alinéas 2 à 5 en conflit avec CD24. |
| **CD39** | Marie Pochon (EcoS) | `CD26` | Consultation en mairie du dossier papier après l'alinéa 1er en concurrence avec la version de CD26. |
| **CD38** | Marie Pochon (EcoS) | `CD62` | Triplement du délai de participation du public (3 mois vs 1 mois) à l'alinéa 2. |
| **CD11** | Jean-François Coulomme (LFI-NFP) | `CD9` | Restriction du champ d'application après l'alinéa 5 en concurrence avec le débat public de CD9. |

### Article 31 (6 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CL12** | Sandra Regol (EcoS) | `CL4` | Encadrement temporel des fouilles de véhicules à l'alinéa 2 (dates fixes vs durée stricte des Jeux). |
| **CL4** | Marie-José Allemand (SOC) | `CL12` | Restriction des fouilles à la seule durée des Jeux à l'alinéa 2 en concurrence avec CL12. |
| **CL48** | Émilie Bonnivard (DR) | `CL12` | Extension du périmètre de fouille aux bagages à l'alinéa 2 en concurrence avec l'encadrement temporel. |
| **CL38** | Jean-François Coulomme (LFI-NFP) | `CL10` | Préservation expresse des droits des passagers à l'alinéa 2 en concurrence avec CL10. |
| **CL11** | Sandra Regol (EcoS) | `CL23` | Exigence d'habilitation préalable des agents de sécurité in fine en concurrence avec le non-profilage de CL23. |
| **CL23** | Sandra Regol (EcoS) | `CL11` | Interdiction expresse de discrimination et profilage lors des contrôles in fine en concurrence avec CL11. |

### Article PREMIER (4 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **AC60** | Jean-François Coulomme (LFI-NFP) | `AC64` | Suppression totale de l'article 1er en conflit direct avec les compléments rédactionnels concurrents. |
| **AC64** | Élisa Martin (LFI-NFP) | `AC60` | Complète l'alinéa unique par une réserve dérogatoire en concurrence avec la suppression de l'article. |
| **AC62** | Jean-François Coulomme (LFI-NFP) | `AC65` | Adjonction d'un alinéa in fine sur l'évaluation financière en concurrence avec le plafonnement salarial de AC65. |
| **AC65** | Élisa Martin (LFI-NFP) | `AC62` | Adjonction d'un alinéa in fine sur les rémunérations des dirigeants en concurrence avec AC62. |

### Article 16 (4 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **AC106** | Jean-François Coulomme (LFI-NFP) | `AC27` | Suppression de l'article 16 en concurrence avec les aménagements dérogatoires de l'alinéa 4. |
| **AC27** | Bertrand Sorre (EPR) | `AC4` | Concurrence rédactionnelle sur la prise en compte des servitudes à l'alinéa 4. |
| **AC4** | Bertrand Sorre (EPR) | `AC28` | Ajustement de référence juridique à l'alinéa 4 en concurrence avec la suppression de AC28. |
| **AC28** | Bertrand Sorre (EPR) | `AC4` | Suppression de la référence à la loi de 1892 à l'alinéa 4 en concurrence avec AC4. |

### Article APRÈS 5 (3 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **AC76** | Jean-François Coulomme (LFI-NFP) | `AC1` | Conditionnement des financements publics du COJOP en concurrence avec le rapport financier de AC1. |
| **AC1** | Frédéric Maillot (GDR) | `AC76` | Demande de rapport préalable d'étape sur les coûts avant mars 2026 en concurrence avec AC76. |
| **AC63** | Élisa Martin (LFI-NFP) | `AC47` | Rapport à 6 ans après promulgation en concurrence avec le rapport de clôture à 6 mois de AC47. |

### Article 18 BIS (3 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CD68** | Olga Givernet (EPR) | `CD12` | Réécriture globale de l'article 18 BIS en concurrence frontale avec les amendements de suppression totale. |
| **CD52** | Joël Bruneau (LIOT) | `CD68` | Ajout d'exclusions territoriales in fine en concurrence avec le périmètre fixé par CD68. |
| **AC138** | Joël Bruneau (LIOT) | `CD68` | Clause d'exclusion in fine concurrente encadrant la portée dérogatoire de l'article 18 BIS. |

### Article 28 (3 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **AC29** | PA795278 (HOR) | `AC30` | Concurrence rédactionnelle sur le recensement des professionnels à la 1re phrase de l'alinéa 14. |
| **AC30** | PA795278 (HOR) | `AC12` | Concurrence syntaxique sur la mission des professionnels à la 1re phrase de l'alinéa 14. |
| **AC12** | PA795278 (HOR) | `AC29` | Concurrence sémantique sur l'évaluation de l'impact/conséquences à la 1re phrase de l'alinéa 14. |

### Article 32 (3 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CL36** | Élisa Martin (LFI-NFP) | `CL49` | Suppression totale de l'article 32 en concurrence directe avec l'aménagement des sanctions pénales. |
| **CL49** | Émilie Bonnivard (DR) | `CL36` | Restriction de l'obligation de signalement aux pilotes professionnels à l'alinéa 3 en conflit avec CL36. |
| **CL5** | Marie-José Allemand (SOC) | `CL36` | Suppression de la peine d'emprisonnement à l'alinéa 7 en concurrence avec la suppression totale de CL36. |

### Article 33 (3 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CL35** | Élisa Martin (LFI-NFP) | `CL59` | Suppression de l'article 33 en concurrence avec l'extension de la neutralisation des drones. |
| **CL59** | Julien Rancoule (RN) | `CL35` | Extension des matériels de brouillage en tête d'article en conflit avec la suppression de CL35. |
| **CL34** | Élisa Martin (LFI-NFP) | `CL35` | Création d'un registre de traçabilité des brouillages in fine en concurrence avec la suppression de CL35. |

### Article APRÈS 35 (3 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CL28** | Élisa Martin (LFI-NFP) | `CL37` | Rapport à 6 mois sur l'impact de la VSA sur les libertés publiques en concurrence avec CL37 et CL56. |
| **CL37** | Élisa Martin (LFI-NFP) | `CL28` | Rapport à 6 mois sur l'efficacité policière de la VSA en concurrence avec l'évaluation des libertés de CL28. |
| **CL56** | Élisa Martin (LFI-NFP) | `CL28` | Rapport d'évaluation à 5 ans de la VSA en concurrence avec les rapports semestriels de CL28 et CL37. |

### Article 4 (2 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **AC102** | Jean-François Coulomme (LFI-NFP) | `AC103` | Suppression totale de l'article 4 en conflit direct avec son extension juridictionnelle par AC103. |
| **AC103** | Jean-François Coulomme (LFI-NFP) | `AC102` | Extension de la compétence des juridictions françaises en concurrence avec la suppression de l'article. |

### Article 8 (2 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CF2** | Benjamin Dirx (EPR) | `CF1` | Concurrence sur les critères d'éligibilité et de subventionnement des associations sportives à l'alinéa 1er. |
| **CF1** | Jean-Claude Raux (EcoS) | `CF2` | Suppression des critères restrictifs de durée à l'alinéa 1er en concurrence avec CF2. |

### Article 9 (2 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **AC115** | Jean-François Coulomme (LFI-NFP) | `AC114` | Adjonction de groupements d'employeurs in fine en concurrence avec l'objectif programmatique de AC114. |
| **AC114** | Jean-François Coulomme (LFI-NFP) | `AC115` | Disposition programmatique in fine sur les agents de sécurité en concurrence avec AC115. |

### Article APRÈS 12 (2 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CD23** | Denis Fégné (SOC) | `CD10` | Obligation de débat public départemental en concurrence avec le rapport d'évaluation de CD10. |
| **CD10** | Élisa Martin (LFI-NFP) | `CD23` | Rapport semestriel sur la concertation publique en concurrence avec le débat préalable de CD23. |

### Article 14 (2 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CE11** | Jean-Claude Raux (EcoS) | `CE2` | Suppression totale de l'article 14 en conflit direct avec la suppression partielle des alinéas 2 et 3 de CE2. |
| **CE2** | Jean-François Coulomme (LFI-NFP) | `CE11` | Suppression des alinéas 2 et 3 en concurrence avec la suppression totale de l'article par CE11. |

### Article 34 (2 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CL32** | Élisa Martin (LFI-NFP) | `CL15` | Suppression de la transmission automatique à l'alinéa 5 en concurrence avec la substitution de CL15. |
| **CL15** | Sandra Regol (EcoS) | `CL32` | Substitution de la qualification de transmission à l'alinéa 5 en concurrence avec CL32. |

### Article APRÈS 3 BIS (1 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CD69** | Julie Lechanteux (RN) | `CD22` | Demande de rapport gouvernemental post-Jeux en concurrence avec l'évaluation Cour des comptes de CD22. |

### Article APRÈS 8 (1 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CF5** | Jean-Claude Raux (EcoS) | `CF4` | Création d'un Comité national de suivi des dépenses en concurrence avec le rapport d'évaluation de CF4. |

### Article 17 (1 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CE12** | Jean-Claude Raux (EcoS) | `CD25` | Suppression de la seconde phrase de l'alinéa 1er en concurrence avec les précisions apportées par CD25. |

### Article 18 (1 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CE4** | Jean-François Coulomme (LFI-NFP) | `CD63` | Suppression totale de l'article 18 en concurrence directe avec la réduction de délai portée par CD63. |

### Article 22 (1 amendements en discussion commune)

| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |
| :--- | :--- | :---: | :--- |
| **CD14** | Élisa Martin (LFI-NFP) | `CD54` | Suppression totale de l'article 22 en concurrence avec l'encadrement des voies réservées de CD54. |

---

## Section 3 : Tableau récapitulatif condensé des 341 amendements

Format strict d'une seule ligne par amendement :

| N° | Article | Auteur (Groupe) | Statut Témoin | Cible | Justification (1 phrase) |
| :--- | :--- | :--- | :---: | :---: | :--- |
| AC137 | 5 | Joël Bruneau (LIOT) | Isolé | — | Seul amendement déposé sur cet article. |
| AC52 | 5 | Jean-Claude Raux (EcoS) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC140 | 11 | Bertrand Sorre (EPR) | Isolé | — | Suppression de la dernière phrase de l'alinéa 3 sans concurrence sur cette subdivision. |
| AC15 | 11 | Bertrand Sorre (EPR) | Isolé | — | Suppression ciblée des alinéas 12 et 13 portant sur une dérogation distincte de AC140. |
| AC67 | AVANT PREMIER | Jean-François Coulomme (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC69 | AVANT PREMIER | Jean-François Coulomme (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC60 | PREMIER | Jean-François Coulomme (LFI-NFP) | Discussion commune | AC64 | Suppression totale de l'article 1er en conflit direct avec les compléments rédactionnels concurrents. |
| AC64 | PREMIER | Élisa Martin (LFI-NFP) | Discussion commune | AC60 | Complète l'alinéa unique par une réserve dérogatoire en concurrence avec la suppression de l'article. |
| AC71 | PREMIER | Jean-François Coulomme (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC62 | PREMIER | Jean-François Coulomme (LFI-NFP) | Discussion commune | AC65 | Adjonction d'un alinéa in fine sur l'évaluation financière en concurrence avec le plafonnement salarial de AC65. |
| AC65 | PREMIER | Élisa Martin (LFI-NFP) | Discussion commune | AC62 | Adjonction d'un alinéa in fine sur les rémunérations des dirigeants en concurrence avec AC62. |
| AC61 | APRÈS PREMIER | Élisa Martin (LFI-NFP) | Isolé | — | Seul amendement déposé sur cet article. |
| AC24 | 2 | Christophe Proença (SOC) | Isolé | — | Seul amendement déposé sur cet article. |
| AC54 | 3 | Jean-Claude Raux (EcoS) | Identique | AC78 | Chef de file d'amendements identiques (partagé avec AC78). |
| AC78 | 3 | Jean-François Coulomme (LFI-NFP) | Identique | AC54 | Dispositif rigoureusement identique déposé par un autre député. |
| AC128 | 3 | Élisa Martin (LFI-NFP) | Discussion commune | AC81 | Concurrence directe sur les délais dérogatoires de publicité à l'alinéa 1er. |
| AC81 | 3 | Jean-François Coulomme (LFI-NFP) | Discussion commune | AC128 | Concurrence directe sur la date d'entrée en vigueur de la dérogation publicitaire à l'alinéa 1er. |
| AC18 | 3 | Christophe Proença (SOC) | Isolé | — | Modification ponctuelle des critères de densité sans concurrence sur l'alinéa 3. |
| AC19 | 3 | Christophe Proença (SOC) | Discussion commune | AC129 | Concurrence sur le champ des dérogations d'affichage et de publicité à l'alinéa 5. |
| AC21 | 3 | Christophe Proença (SOC) | Discussion commune | AC129 | Précision temporelle sur l'affichage à l'alinéa 5 en concurrence avec la substitution globale de AC129. |
| AC129 | 3 | Élisa Martin (LFI-NFP) | Discussion commune | AC19 | Substitution du calendrier d'affichage à l'alinéa 5 en concurrence avec la suppression de AC19. |
| AC31 | 3 | Christophe Proença (SOC) | Discussion commune | AC20 | Concurrence rédactionnelle sur l'encadrement des nuisances à la seconde phrase de l'alinéa 6 (optimiser vs limiter). |
| AC20 | 3 | Christophe Proença (SOC) | Discussion commune | AC31 | Concurrence rédactionnelle sur la qualification des impacts/nuisances à la seconde phrase de l'alinéa 6. |
| AC130 | 3 | Élisa Martin (LFI-NFP) | Isolé | — | Seul amendement ciblant les délais d'affichage spécifiques de l'alinéa 7. |
| AC80 | 3 | Élisa Martin (LFI-NFP) | Discussion commune | AC82 | Concurrence sur la période temporelle des dérogations publicitaires autour des sites à l'alinéa 8. |
| AC82 | 3 | Élisa Martin (LFI-NFP) | Discussion commune | AC80 | Concurrence sur le rayon kilométrique de restriction publicitaire à l'alinéa 8 (500m vs 200m). |
| AC86 | 3 | Élisa Martin (LFI-NFP) | Discussion commune | AC82 | Suppression de la seconde moitié de l'alinéa 8 en concurrence avec les seuils kilométriques de AC82. |
| AC133 | 3 | Jean-François Coulomme (LFI-NFP) | Isolé | — | Suppression ciblée des alinéas 9 et 10 sans concurrent direct sur ces subdivisions. |
| AC87 | 3 | Jean-François Coulomme (LFI-NFP) | Isolé | — | Suppression ciblée de l'alinéa 13 sans concurrent direct. |
| AC84 | 3 | Jean-François Coulomme (LFI-NFP) | Isolé | — | Insertion d'un alinéa autonome interdisant la publicité pour énergies fossiles après l'alinéa 14. |
| AC88 | 3 | Élisa Martin (LFI-NFP) | Discussion commune | AC131 | Suppression globale des alinéas 15 à 17 en conflit direct avec les modifications d'alinéa de AC131 et AC22. |
| AC131 | 3 | Élisa Martin (LFI-NFP) | Discussion commune | AC22 | Concurrence directe sur les dates limites de la dérogation publicitaire à l'alinéa 16. |
| AC22 | 3 | Christophe Proença (SOC) | Discussion commune | AC131 | Concurrence rédactionnelle sur les affichages autorisés à la 2de phrase de l'alinéa 16. |
| AC23 (Rect) | 3 | Christophe Proença (SOC) | Discussion commune | AC132 | Concurrence directe sur les dérogations publicitaires et dates d'application de l'alinéa 18. |
| AC132 | 3 | Élisa Martin (LFI-NFP) | Discussion commune | AC23 (Rect) | Concurrence directe sur le calendrier d'interdiction publicitaire à l'alinéa 18. |
| AC55 | 3 | Jean-Claude Raux (EcoS) | Discussion commune | AC132 | Insertion d'un alinéa d'interdiction après l'alinéa 18 en concurrence avec le régime dérogatoire de AC132. |
| AC58 | APRÈS 3 | Jean-Claude Raux (EcoS) | Isolé | — | Amendement sans dispositif opérationnel. |
| CD50 | 3 BIS | Alexis Jolly (RN) | Discussion commune | CD18 | Suppression de l'article 3 BIS en concurrence frontale avec la réécriture globale de CD18. |
| CD18 | 3 BIS | Denis Fégné (SOC) | Discussion commune | CD68 | Réécriture globale concurrente de l'article 3 BIS en conflit direct avec la version de CD68. |
| CD74 | 3 BIS | Marie Pochon (EcoS) | Isolé | — | Insertion d'un 5° spécifique sur l'artificialisation après l'alinéa 7 sans concurrent direct. |
| CD19 | 3 BIS | Denis Fégné (SOC) | Discussion commune | CD60 | Concurrence sur le délai de remise du bilan environnemental à l'alinéa 1er (12 mois vs 24 mois). |
| CD20 | 3 BIS | Denis Fégné (SOC) | Discussion commune | CD32 | Concurrence sur les institutions associées au rapport (Haut Conseil pour le Climat) à l'alinéa 1er. |
| CD60 | 3 BIS | Olga Givernet (EPR) | Identique | AC155 | Chef de file d'amendements identiques (partagé avec AC155). |
| CD32 | 3 BIS | Marie Pochon (EcoS) | Identique | AC156 | Chef de file d'amendements identiques (partagé avec AC156). |
| CD16 | 3 BIS | Jean-François Coulomme (LFI-NFP) | Identique | AC157 | Chef de file d'amendements identiques (partagé avec AC157). |
| CD46 | 3 BIS | Élisa Martin (LFI-NFP) | Discussion commune | CD16 | Concurrence sur le contenu obligatoire du rapport environnemental à l'alinéa 1er. |
| CD33 | 3 BIS | Marie Pochon (EcoS) | Discussion commune | CD47 | Concurrence sur l'association des associations environnementales à l'alinéa 1er. |
| CD47 | 3 BIS | Jean-François Coulomme (LFI-NFP) | Discussion commune | CD33 | Concurrence sur la formulation de la contribution associative au bilan carbone à l'alinéa 1er. |
| CD21 | 3 BIS | Denis Fégné (SOC) | Discussion commune | CD18 | Insertion d'un I bis créant un mécanisme d'indemnisation financière en suite du rapport. |
| CD61 | 3 BIS | Olga Givernet (EPR) | Identique | AC158 | Chef de file d'amendements identiques (partagé avec AC158). |
| CD34 | 3 BIS | Marie Pochon (EcoS) | Isolé | — | Complément in fine interdisant les constructions pérennes en zone naturelle protégée. |
| CD22 | APRÈS 3 BIS | Denis Fégné (SOC) | Identique | CD67 | Chef de file d'amendements identiques (partagé avec CD67). |
| CD67 | APRÈS 3 BIS | Marie Pochon (EcoS) | Identique | CD22 | Dispositif rigoureusement identique déposé par un autre député. |
| CD69 | APRÈS 3 BIS | Julie Lechanteux (RN) | Discussion commune | CD22 | Demande de rapport gouvernemental post-Jeux en concurrence avec l'évaluation Cour des comptes de CD22. |
| AC102 | 4 | Jean-François Coulomme (LFI-NFP) | Discussion commune | AC103 | Suppression totale de l'article 4 en conflit direct avec son extension juridictionnelle par AC103. |
| AC103 | 4 | Jean-François Coulomme (LFI-NFP) | Discussion commune | AC102 | Extension de la compétence des juridictions françaises en concurrence avec la suppression de l'article. |
| AC136 | APRÈS 4 | Joël Bruneau (LIOT) | Isolé | — | Seul amendement déposé sur cet article. |
| AC37 | APRÈS 5 | Claudia Rouaux (SOC) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC76 | APRÈS 5 | Jean-François Coulomme (LFI-NFP) | Discussion commune | AC1 | Conditionnement des financements publics du COJOP en concurrence avec le rapport financier de AC1. |
| AC1 | APRÈS 5 | Frédéric Maillot (GDR) | Discussion commune | AC76 | Demande de rapport préalable d'étape sur les coûts avant mars 2026 en concurrence avec AC76. |
| AC47 | APRÈS 5 | Christophe Proença (SOC) | Identique | AC45 | Chef de file d'amendements identiques (partagé avec AC45). |
| AC45 | APRÈS 5 | Claudia Rouaux (SOC) | Identique | AC47 | Dispositif rigoureusement identique déposé par un autre député. |
| AC63 | APRÈS 5 | Élisa Martin (LFI-NFP) | Discussion commune | AC47 | Rapport à 6 ans après promulgation en concurrence avec le rapport de clôture à 6 mois de AC47. |
| AC32 | 6 | Christophe Proença (SOC) | Discussion commune | AC33 | Concurrence sur la qualification de l'approbation ministérielle à la 1re phrase de l'alinéa unique. |
| AC33 | 6 | Christophe Proença (SOC) | Discussion commune | AC32 | Suppression de la mention des dispositions législatives à la 1re phrase de l'alinéa unique en concurrence avec AC32. |
| AC16 | 6 | Christophe Proença (SOC) | Discussion commune | AC34 | Extension aux violences sexistes à la 2de phrase de l'alinéa unique en concurrence avec AC34 et AC25. |
| AC34 | 6 | Christophe Proença (SOC) | Discussion commune | AC25 | Réécriture de la fin de la 2de phrase de l'alinéa unique en concurrence directe avec AC25. |
| AC44 | 6 | Claudia Rouaux (SOC) | Discussion commune | AC25 | Insertion d'une obligation de formation aux discriminations en concurrence avec la rédaction de AC25. |
| AC25 | 6 | Géraldine Bannier (Dem) | Discussion commune | AC34 | Réécriture concurrente de la fin de la 2de phrase de l'alinéa unique sur les discriminations. |
| AC105 | 6 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC48 | APRÈS 6 | Stéphane Viry (LIOT) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC17 | 7 | Christophe Proença (SOC) | Identique | AC46 | Chef de file d'amendements identiques (partagé avec AC46). |
| AC46 | 7 | Claudia Rouaux (SOC) | Identique | AC17 | Dispositif rigoureusement identique déposé par un autre député. |
| AC134 | 7 | Jean-Claude Raux (EcoS) | Discussion commune | AC17 | Rétablissement concurrent du paragraphe I sur la désignation des parlementaires au conseil d'administration. |
| AC53 | 7 | Jean-Claude Raux (EcoS) | Discussion commune | AC59 | Insertion d'un I bis plafonnant les rémunérations des dirigeants en concurrence avec AC59. |
| AC59 | 7 | Soumya Bourouaha (GDR) | Discussion commune | AC53 | Plafonnement des dix principales rémunérations à l'alinéa 1 bis en concurrence avec AC53. |
| AC135 | 7 | Jean-François Coulomme (LFI-NFP) | Discussion commune | AC111 | Suppression du seuil restrictif de dix rémunérations en concurrence avec les seuils de AC111 et AC141. |
| AC111 | 7 | Élisa Martin (LFI-NFP) | Discussion commune | AC141 | Extension de la transparence aux 100 premières rémunérations à l'alinéa 2 (vs 20 pour AC141). |
| AC141 | 7 | Christophe Proença (SOC) | Discussion commune | AC111 | Extension de la transparence aux 20 premières rémunérations à l'alinéa 2 (vs 100 pour AC111). |
| AC113 | 7 | Jean-François Coulomme (LFI-NFP) | Discussion commune | AC109 | Plan d'encadrement des écarts salariaux complétant l'alinéa 2 en concurrence avec le débat de AC109. |
| AC109 | 7 | Élisa Martin (LFI-NFP) | Discussion commune | AC113 | Exigence d'un débat parlementaire complétant l'alinéa 2 en concurrence avec AC113. |
| AC49 | 7 | Soumya Bourouaha (GDR) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC50 | APRÈS 7 | Soumya Bourouaha (GDR) | Isolé | — | Seul amendement déposé sur cet article. |
| CF2 | 8 | Benjamin Dirx (EPR) | Discussion commune | CF1 | Concurrence sur les critères d'éligibilité et de subventionnement des associations sportives à l'alinéa 1er. |
| CF1 | 8 | Jean-Claude Raux (EcoS) | Discussion commune | CF2 | Suppression des critères restrictifs de durée à l'alinéa 1er en concurrence avec CF2. |
| CF3 | 8 | Benjamin Dirx (EPR) | Identique | AC180 | Chef de file d'amendements identiques (partagé avec AC180). |
| CF5 | APRÈS 8 | Jean-Claude Raux (EcoS) | Discussion commune | CF4 | Création d'un Comité national de suivi des dépenses en concurrence avec le rapport d'évaluation de CF4. |
| CF4 | APRÈS 8 | Jean-Claude Raux (EcoS) | Isolé | — | Modifie un point spécifique non contesté par les autres amendements de l'article APRÈS 8. |
| AC115 | 9 | Jean-François Coulomme (LFI-NFP) | Discussion commune | AC114 | Adjonction de groupements d'employeurs in fine en concurrence avec l'objectif programmatique de AC114. |
| AC114 | 9 | Jean-François Coulomme (LFI-NFP) | Discussion commune | AC115 | Disposition programmatique in fine sur les agents de sécurité en concurrence avec AC115. |
| AC116 | 9 BIS | Élisa Martin (LFI-NFP) | Isolé | — | Seul amendement déposé sur cet article. |
| AC117 | 10 | Jean-François Coulomme (LFI-NFP) | Isolé | — | Seul amendement déposé sur cet article. |
| AC108 | APRÈS 10 | Jean-François Coulomme (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC112 | APRÈS 10 | Élisa Martin (LFI-NFP) | Isolé | — | Seul amendement déposé sur cet article. |
| AC2 | APRÈS 11 | Christophe Proença (SOC) | Identique | AC35 | Chef de file d'amendements identiques (partagé avec AC35). |
| AC35 | APRÈS 11 | Belkhir Belhaddad (SOC) | Identique | AC2 | Dispositif rigoureusement identique déposé par un autre député. |
| CD7 | 12 | Jean-François Coulomme (LFI-NFP) | Identique | CD35 | Chef de file d'amendements identiques (partagé avec CD35). |
| CD35 | 12 | Marie Pochon (EcoS) | Identique | CD7 | Dispositif rigoureusement identique déposé par un autre député. |
| CD24 | 12 | Denis Fégné (SOC) | Discussion commune | CD36 | Réécriture globale du régime de participation du public en concurrence avec les réécritures partielles. |
| CD25 | 12 | Denis Fégné (SOC) | Discussion commune | CD3 | Précision sur la démarche environnementale à l'alinéa 1er en concurrence avec le caractère facultatif de CD3. |
| CD3 | 12 | Xavier Roseren (HOR) | Identique | AC159 | Chef de file d'amendements identiques (partagé avec AC159). |
| CD36 | 12 | Marie Pochon (EcoS) | Discussion commune | CD24 | Substitution de la base légale de consultation (L. 123-1) et suppression des alinéas 2 à 5 en conflit avec CD24. |
| CD8 | 12 | Élisa Martin (LFI-NFP) | Isolé | — | Modifie un point spécifique non contesté par les autres amendements de l'article 12. |
| CD26 | 12 | Denis Fégné (SOC) | Identique | AC160 | Chef de file d'amendements identiques (partagé avec AC160). |
| CD39 | 12 | Marie Pochon (EcoS) | Discussion commune | CD26 | Consultation en mairie du dossier papier après l'alinéa 1er en concurrence avec la version de CD26. |
| CD38 | 12 | Marie Pochon (EcoS) | Discussion commune | CD62 | Triplement du délai de participation du public (3 mois vs 1 mois) à l'alinéa 2. |
| CD62 | 12 | Olga Givernet (EPR) | Identique | AC161 | Chef de file d'amendements identiques (partagé avec AC161). |
| CD63 | 12 | Olga Givernet (EPR) | Identique | AC162 | Chef de file d'amendements identiques (partagé avec AC162). |
| CD11 | 12 | Jean-François Coulomme (LFI-NFP) | Discussion commune | CD9 | Restriction du champ d'application après l'alinéa 5 en concurrence avec le débat public de CD9. |
| CD9 | 12 | Jean-François Coulomme (LFI-NFP) | Identique | CD37 | Chef de file d'amendements identiques (partagé avec CD37). |
| CD37 | 12 | Marie Pochon (EcoS) | Identique | CD9 | Dispositif rigoureusement identique déposé par un autre député. |
| CD23 | APRÈS 12 | Denis Fégné (SOC) | Discussion commune | CD10 | Obligation de débat public départemental en concurrence avec le rapport d'évaluation de CD10. |
| CD51 | APRÈS 12 | Alexis Jolly (RN) | Isolé | — | Amendement sans dispositif opérationnel. |
| CD72 | APRÈS 12 | Romain Daubié (Dem) | Isolé | — | Amendement sans dispositif opérationnel. |
| CD73 | APRÈS 12 | Romain Daubié (Dem) | Isolé | — | Amendement sans dispositif opérationnel. |
| CD4 | APRÈS 12 | Fabrice Brun (DR) | Isolé | — | Amendement sans dispositif opérationnel. |
| CD10 | APRÈS 12 | Élisa Martin (LFI-NFP) | Discussion commune | CD23 | Rapport semestriel sur la concertation publique en concurrence avec le débat préalable de CD23. |
| CE1 | 13 | Élisa Martin (LFI-NFP) | Identique | CE9 | Chef de file d'amendements identiques (partagé avec CE9). |
| CE9 | 13 | Jean-Claude Raux (EcoS) | Identique | CE1 | Dispositif rigoureusement identique déposé par un autre député. |
| CE10 | 13 | Jean-Claude Raux (EcoS) | Isolé | — | Modifie un point spécifique non contesté par les autres amendements de l'article 13. |
| CE14 | 13 | Valérie Rossi (SOC) | Isolé | — | Modifie un point spécifique non contesté par les autres amendements de l'article 13. |
| CE15 | 13 | Valérie Rossi (SOC) | Isolé | — | Modifie un point spécifique non contesté par les autres amendements de l'article 13. |
| CE21 | 13 | Romain Daubié (Dem) | Identique | AC143 | Chef de file d'amendements identiques (partagé avec AC143). |
| CE11 | 14 | Jean-Claude Raux (EcoS) | Discussion commune | CE2 | Suppression totale de l'article 14 en conflit direct avec la suppression partielle des alinéas 2 et 3 de CE2. |
| CE2 | 14 | Jean-François Coulomme (LFI-NFP) | Discussion commune | CE11 | Suppression des alinéas 2 et 3 en concurrence avec la suppression totale de l'article par CE11. |
| AC51 | 15 | Jean-Claude Raux (EcoS) | Identique | AC104 | Chef de file d'amendements identiques (partagé avec AC104). |
| AC104 | 15 | Élisa Martin (LFI-NFP) | Identique | AC51 | Dispositif rigoureusement identique déposé par un autre député. |
| AC3 | 15 | Bertrand Sorre (EPR) | Isolé | — | Remplacement rédactionnel ponctuel à l'alinéa 2 sans concurrence sur cette subdivision. |
| AC106 | 16 | Jean-François Coulomme (LFI-NFP) | Discussion commune | AC27 | Suppression de l'article 16 en concurrence avec les aménagements dérogatoires de l'alinéa 4. |
| AC5 | 16 | Bertrand Sorre (EPR) | Isolé | — | Extension de l'obligation au démontage et enlèvement à l'alinéa 1er sans concurrent direct. |
| AC27 | 16 | Bertrand Sorre (EPR) | Discussion commune | AC4 | Concurrence rédactionnelle sur la prise en compte des servitudes à l'alinéa 4. |
| AC4 | 16 | Bertrand Sorre (EPR) | Discussion commune | AC28 | Ajustement de référence juridique à l'alinéa 4 en concurrence avec la suppression de AC28. |
| AC28 | 16 | Bertrand Sorre (EPR) | Discussion commune | AC4 | Suppression de la référence à la loi de 1892 à l'alinéa 4 en concurrence avec AC4. |
| CE12 | 17 | Jean-Claude Raux (EcoS) | Discussion commune | CD25 | Suppression de la seconde phrase de l'alinéa 1er en concurrence avec les précisions apportées par CD25. |
| CE22 | 17 | Romain Daubié (Dem) | Identique | AC144 | Chef de file d'amendements identiques (partagé avec AC144). |
| CE3 | 17 | Élisa Martin (LFI-NFP) | Identique | CE13 | Chef de file d'amendements identiques (partagé avec CE13). |
| CE13 | 17 | Jean-Claude Raux (EcoS) | Identique | CE3 | Dispositif rigoureusement identique déposé par un autre député. |
| CE4 | 18 | Jean-François Coulomme (LFI-NFP) | Discussion commune | CD63 | Suppression totale de l'article 18 en concurrence directe avec la réduction de délai portée par CD63. |
| CE23 | 18 | Romain Daubié (Dem) | Identique | AC145 | Chef de file d'amendements identiques (partagé avec AC145). |
| CD12 | 18 BIS | Jean-François Coulomme (LFI-NFP) | Identique | CD27 | Chef de file d'amendements identiques (partagé avec CD27). |
| CD27 | 18 BIS | Denis Fégné (SOC) | Identique | CD12 | Dispositif rigoureusement identique déposé par un autre député. |
| CD40 | 18 BIS | Marie Pochon (EcoS) | Identique | CD12 | Dispositif rigoureusement identique déposé par un autre député. |
| CD68 | 18 BIS | Olga Givernet (EPR) | Discussion commune | CD12 | Réécriture globale de l'article 18 BIS en concurrence frontale avec les amendements de suppression totale. |
| CD52 | 18 BIS | Joël Bruneau (LIOT) | Discussion commune | CD68 | Ajout d'exclusions territoriales in fine en concurrence avec le périmètre fixé par CD68. |
| CD48 | APRÈS 18 BIS | Alexis Jolly (RN) | Isolé | — | Seul amendement déposé sur cet article. |
| CE5 | 19 | Élisa Martin (LFI-NFP) | Identique | CE8 | Chef de file d'amendements identiques (partagé avec CE8). |
| CE8 | 19 | Jean-Claude Raux (EcoS) | Identique | CE5 | Dispositif rigoureusement identique déposé par un autre député. |
| CE24 | 19 | Romain Daubié (Dem) | Identique | AC146 | Chef de file d'amendements identiques (partagé avec AC146). |
| CE27 | 20 | Romain Daubié (Dem) | Identique | AC149 | Chef de file d'amendements identiques (partagé avec AC149). |
| CE6 | 20 | Jean-François Coulomme (LFI-NFP) | Isolé | — | Ajout d'un avis du Conseil national de la montagne à l'alinéa 2 sans concurrence sur cette subdivision. |
| CE28 | 20 | Romain Daubié (Dem) | Identique | AC150 | Chef de file d'amendements identiques (partagé avec AC150). |
| CE25 | 20 | Romain Daubié (Dem) | Identique | AC147 | Chef de file d'amendements identiques (partagé avec AC147). |
| CE16 | 20 | Valérie Rossi (SOC) | Isolé | — | Modification de l'échéance temporelle à l'alinéa 6 (2030 au lieu de 2032) sans concurrent direct. |
| CD28 | 21 | Denis Fégné (SOC) | Isolé | — | Modifie un point spécifique non contesté par les autres amendements de l'article 21. |
| CD75 | 21 | Marie Pochon (EcoS) | Discussion commune | CD28 | Garantie environnementale à l'alinéa 4 en concurrence avec la réécriture globale de CD28. |
| CD70 | 21 | Julie Lechanteux (RN) | Discussion commune | CD28 | Renforcement de la sécurité physique des transports en concurrence avec la réécriture de CD28. |
| CD49 | 21 | Alexis Jolly (RN) | Discussion commune | CD13 | Volet mobilités partagées complétant le rapport in fine en concurrence avec les propositions de CD13. |
| CD13 | 21 | Jean-François Coulomme (LFI-NFP) | Discussion commune | CD49 | Volet pérennité des infrastructures complétant le rapport in fine en concurrence avec CD49 et CD29. |
| CD29 | 21 | Denis Fégné (SOC) | Discussion commune | CD5 | Précision sur les liaisons ferroviaires complétant le rapport in fine en concurrence avec CD5. |
| CD5 | 21 | Xavier Roseren (HOR) | Discussion commune | CD6 | Volet ferroviaire détaillé en 7 alinéas complétant le rapport in fine en concurrence avec CD6. |
| CD6 | 21 | Xavier Roseren (HOR) | Discussion commune | CD5 | Sous-volet transports du quotidien complétant le rapport in fine en concurrence avec CD5. |
| CD2 | 21 | Xavier Roseren (HOR) | Isolé | — | Amendement sans dispositif opérationnel. |
| CD41 | 21 | Marie Pochon (EcoS) | Discussion commune | CD49 | Rattachement des projets d'intermodalité complétant le rapport in fine en concurrence avec CD49. |
| CD43 | APRÈS 21 | Marie Pochon (EcoS) | Isolé | — | Exigence autonome d'exemplarité environnementale sur les flottes automobiles publiques. |
| CD42 | APRÈS 21 | Marie Pochon (EcoS) | Identique | AC165 | Chef de file d'amendements identiques (partagé avec AC165). |
| CD14 | 22 | Élisa Martin (LFI-NFP) | Discussion commune | CD54 | Suppression totale de l'article 22 en concurrence avec l'encadrement des voies réservées de CD54. |
| CD54 | 22 | Olga Givernet (EPR) | Identique | AC166 | Chef de file d'amendements identiques (partagé avec AC166). |
| CD55 | 22 | Olga Givernet (EPR) | Identique | AC167 | Chef de file d'amendements identiques (partagé avec AC167). |
| CD30 | 22 | Denis Fégné (SOC) | Identique | AC168 | Chef de file d'amendements identiques (partagé avec AC168). |
| CD56 | 22 | Olga Givernet (EPR) | Identique | AC169 | Chef de file d'amendements identiques (partagé avec AC169). |
| CD71 | 22 | Julie Lechanteux (RN) | Isolé | — | Dérogation spécifique pour les communes de moins de 5 000 habitants après l'alinéa 3. |
| CD31 | 22 | Denis Fégné (SOC) | Isolé | — | Validation ministérielle complétant l'alinéa 4 sans concurrent direct. |
| CD57 | 22 | Olga Givernet (EPR) | Identique | AC171 | Chef de file d'amendements identiques (partagé avec AC171). |
| CD58 | 22 | Olga Givernet (EPR) | Identique | AC172 | Chef de file d'amendements identiques (partagé avec AC172). |
| CD59 | 22 | Olga Givernet (EPR) | Identique | AC173 | Chef de file d'amendements identiques (partagé avec AC173). |
| CD15 | 22 | Jean-François Coulomme (LFI-NFP) | Identique | CD17 | Chef de file d'amendements identiques (partagé avec CD17). |
| CD17 | 22 | Pierre Meurin (RN) | Identique | CD15 | Dispositif rigoureusement identique déposé par un autre député. |
| CD44 | 22 | Marie Pochon (EcoS) | Identique | AC174 | Chef de file d'amendements identiques (partagé avec AC174). |
| CD45 | APRÈS 22 | Sébastien Peytavie (EcoS) | Identique | AC175 | Chef de file d'amendements identiques (partagé avec AC175). |
| CE19 | 24 | Vincent Rolland (DR) | Isolé | — | Réécriture ciblée de la fin de l'alinéa 3 sans concurrence directe sur cette disposition. |
| CE20 | 24 | Vincent Rolland (DR) | Identique | AC142 | Chef de file d'amendements identiques (partagé avec AC142). |
| CE26 | 24 | Romain Daubié (Dem) | Identique | AC148 | Chef de file d'amendements identiques (partagé avec AC148). |
| CE7 | 24 | Élisa Martin (LFI-NFP) | Isolé | — | Insertion d'une phrase sur les obligations contractuelles à l'alinéa 5 sans concurrent direct. |
| AC6 | 25 | PA795278 (HOR) | Isolé | — | Substitution de qualification à l'alinéa 1er (affectées vs dédiées) sans concurrent. |
| AC120 | 25 | Jean-François Coulomme (LFI-NFP) | Isolé | — | Interdiction de compensation financière après l'alinéa 2 sans concurrence sur cette division. |
| AC57 | APRÈS 25 | Jean-Claude Raux (EcoS) | Identique | AC73 | Chef de file d'amendements identiques (partagé avec AC73). |
| AC73 | APRÈS 25 | Jean-François Coulomme (LFI-NFP) | Identique | AC57 | Dispositif rigoureusement identique déposé par un autre député. |
| AC74 | APRÈS 25 | Élisa Martin (LFI-NFP) | Isolé | — | Modifie un point spécifique non contesté par les autres amendements de l'article APRÈS 25. |
| AC7 | 26 | PA795278 (HOR) | Isolé | — | Seul amendement déposé sur cet article. |
| AC8 | 27 | PA795278 (HOR) | Isolé | — | Seul amendement déposé sur cet article. |
| AC9 | 27 BIS | Christophe Proença (SOC) | Identique | AC36 | Chef de file d'amendements identiques (partagé avec AC36). |
| AC36 | 27 BIS | Belkhir Belhaddad (SOC) | Identique | AC9 | Dispositif rigoureusement identique déposé par un autre député. |
| AC121 | 27 BIS | Jean-François Coulomme (LFI-NFP) | Identique | AC9 | Dispositif rigoureusement identique déposé par un autre député. |
| AC123 | 27 BIS | Frédéric Maillot (GDR) | Identique | AC9 | Dispositif rigoureusement identique déposé par un autre député. |
| AC10 | 27 TER | Christophe Proença (SOC) | Isolé | — | Seul amendement déposé sur cet article. |
| AC91 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Remplacement de 'sensibilisées' par 'formées' à l'alinéa 5 sans concurrent direct. |
| AC92 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC93 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC94 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC95 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC96 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC97 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC98 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC99 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC100 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC107 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC11 | 28 | PA795278 (HOR) | Isolé | — | Suppression de la mention de compétence territoriale à l'alinéa 6 sans concurrent. |
| AC110 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC29 | 28 | PA795278 (HOR) | Discussion commune | AC30 | Concurrence rédactionnelle sur le recensement des professionnels à la 1re phrase de l'alinéa 14. |
| AC30 | 28 | PA795278 (HOR) | Discussion commune | AC12 | Concurrence syntaxique sur la mission des professionnels à la 1re phrase de l'alinéa 14. |
| AC12 | 28 | PA795278 (HOR) | Discussion commune | AC29 | Concurrence sémantique sur l'évaluation de l'impact/conséquences à la 1re phrase de l'alinéa 14. |
| AC118 | 28 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC13 | 28 | PA795278 (HOR) | Isolé | — | Précision sur la nature professionnelle des ordres à l'alinéa 15 sans concurrent. |
| AC119 | APRÈS 28 | Jean-François Coulomme (LFI-NFP) | Isolé | — | Seul amendement déposé sur cet article. |
| AC14 | 29 | PA795278 (HOR) | Isolé | — | Seul amendement déposé sur cet article. |
| AC85 | 30 | Jean-François Coulomme (LFI-NFP) | Identique | AC124 | Chef de file d'amendements identiques (partagé avec AC124). |
| AC124 | 30 | Soumya Bourouaha (GDR) | Identique | AC85 | Dispositif rigoureusement identique déposé par un autre député. |
| AC75 | 30 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC83 | 30 | Élisa Martin (LFI-NFP) | Discussion commune | AC41 | Suppression des communes limitrophes à l'alinéa 1er en concurrence avec le transfert au maire de AC41. |
| AC40 | 30 | Pierrick Courbon (SOC) | Identique | AC125 | Chef de file d'amendements identiques (partagé avec AC125). |
| AC125 | 30 | Frédéric Maillot (GDR) | Identique | AC40 | Dispositif rigoureusement identique déposé par un autre député. |
| AC41 | 30 | Pierrick Courbon (SOC) | Discussion commune | AC42 | Transfert de la décision dérogatoire au maire sur délibération à l'alinéa 1er (vs arrêté simple pour AC42). |
| AC42 | 30 | Pierrick Courbon (SOC) | Discussion commune | AC41 | Transfert direct au maire de la dérogation dominicale à l'alinéa 1er en concurrence avec AC41. |
| AC56 | 30 | Jean-Claude Raux (EcoS) | Discussion commune | AC38 | Restriction de la période de dérogation dominicale à l'alinéa 1er (février vs trimestre complet). |
| AC38 | 30 | Pierrick Courbon (SOC) | Discussion commune | AC56 | Concurrence sur le calendrier strict de dérogation au repos dominical à l'alinéa 1er. |
| AC43 | 30 | Pierrick Courbon (SOC) | Discussion commune | AC126 | Exigence d'un avis 'conforme' du maire à l'alinéa 2 en concurrence avec l'avis 'favorable' de AC126. |
| AC126 | 30 | Frédéric Maillot (GDR) | Discussion commune | AC43 | Exigence d'un avis 'favorable' du maire à l'alinéa 2 en concurrence avec l'avis 'conforme' de AC43. |
| AC39 | 30 | Pierrick Courbon (SOC) | Discussion commune | AC43 | Délai de prévenance de deux mois complétant l'alinéa 2 en concurrence avec les avis de AC43 et AC126. |
| AC68 | 30 | Jean-François Coulomme (LFI-NFP) | Isolé | — | Garantie anti-préjudice pour les salariés refusant le travail du dimanche à l'alinéa 4. |
| AC79 | 30 | Élisa Martin (LFI-NFP) | Isolé | — | Suppression ciblée de l'alinéa 5 portant sur les dérogations aux conventions collectives. |
| AC72 | 30 | Élisa Martin (LFI-NFP) | Isolé | — | Objectif programmatique in fine sur les permanences d'agents de contrôle du travail. |
| AC77 | 30 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC70 | APRÈS 30 | Élisa Martin (LFI-NFP) | Isolé | — | Seul amendement déposé sur cet article. |
| AC66 | APRÈS 30 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| CL8 | 31 | Sandra Regol (EcoS) | Identique | CL39 | Chef de file d'amendements identiques (partagé avec CL39). |
| CL39 | 31 | Élisa Martin (LFI-NFP) | Identique | CL8 | Dispositif rigoureusement identique déposé par un autre député. |
| CL40 | 31 | Elsa Faucillon (GDR) | Identique | CL8 | Dispositif rigoureusement identique déposé par un autre député. |
| CL12 | 31 | Sandra Regol (EcoS) | Discussion commune | CL4 | Encadrement temporel des fouilles de véhicules à l'alinéa 2 (dates fixes vs durée stricte des Jeux). |
| CL4 | 31 | Marie-José Allemand (SOC) | Discussion commune | CL12 | Restriction des fouilles à la seule durée des Jeux à l'alinéa 2 en concurrence avec CL12. |
| CL2 | 31 | Véronique Riotton (EPR) | Identique | CL9 | Chef de file d'amendements identiques (partagé avec CL9). |
| CL9 | 31 | Sandra Regol (EcoS) | Identique | CL2 | Dispositif rigoureusement identique déposé par un autre député. |
| CL57 | 31 | Paul Molac (LIOT) | Identique | CL2 | Dispositif rigoureusement identique déposé par un autre député. |
| CL48 | 31 | Émilie Bonnivard (DR) | Discussion commune | CL12 | Extension du périmètre de fouille aux bagages à l'alinéa 2 en concurrence avec l'encadrement temporel. |
| CL10 | 31 | Sandra Regol (EcoS) | Identique | AC154 | Chef de file d'amendements identiques (partagé avec AC154). |
| CL38 | 31 | Jean-François Coulomme (LFI-NFP) | Discussion commune | CL10 | Préservation expresse des droits des passagers à l'alinéa 2 en concurrence avec CL10. |
| CL11 | 31 | Sandra Regol (EcoS) | Discussion commune | CL23 | Exigence d'habilitation préalable des agents de sécurité in fine en concurrence avec le non-profilage de CL23. |
| CL23 | 31 | Sandra Regol (EcoS) | Discussion commune | CL11 | Interdiction expresse de discrimination et profilage lors des contrôles in fine en concurrence avec CL11. |
| CL13 | APRÈS 31 | Sandra Regol (EcoS) | Isolé | — | Amendement sans dispositif opérationnel. |
| CL58 | APRÈS 31 | Julien Rancoule (RN) | Isolé | — | Amendement sans dispositif opérationnel. |
| CL36 | 32 | Élisa Martin (LFI-NFP) | Discussion commune | CL49 | Suppression totale de l'article 32 en concurrence directe avec l'aménagement des sanctions pénales. |
| CL49 | 32 | Émilie Bonnivard (DR) | Discussion commune | CL36 | Restriction de l'obligation de signalement aux pilotes professionnels à l'alinéa 3 en conflit avec CL36. |
| CL5 | 32 | Marie-José Allemand (SOC) | Discussion commune | CL36 | Suppression de la peine d'emprisonnement à l'alinéa 7 en concurrence avec la suppression totale de CL36. |
| CL35 | 33 | Élisa Martin (LFI-NFP) | Discussion commune | CL59 | Suppression de l'article 33 en concurrence avec l'extension de la neutralisation des drones. |
| CL59 | 33 | Julien Rancoule (RN) | Discussion commune | CL35 | Extension des matériels de brouillage en tête d'article en conflit avec la suppression de CL35. |
| CL34 | 33 | Élisa Martin (LFI-NFP) | Discussion commune | CL35 | Création d'un registre de traçabilité des brouillages in fine en concurrence avec la suppression de CL35. |
| CL6 | 34 | Marie-José Allemand (SOC) | Identique | CL33 | Chef de file d'amendements identiques (partagé avec CL33). |
| CL33 | 34 | Élisa Martin (LFI-NFP) | Identique | CL6 | Dispositif rigoureusement identique déposé par un autre député. |
| CL41 | 34 | Elsa Faucillon (GDR) | Identique | CL6 | Dispositif rigoureusement identique déposé par un autre député. |
| CL61 | 34 | Pouria Amirshahi (EcoS) | Identique | CL6 | Dispositif rigoureusement identique déposé par un autre député. |
| CL16 | 34 | Sandra Regol (EcoS) | Isolé | — | Ajustement de référence textuelle à l'alinéa 4 sans concurrent direct. |
| CL32 | 34 | Élisa Martin (LFI-NFP) | Discussion commune | CL15 | Suppression de la transmission automatique à l'alinéa 5 en concurrence avec la substitution de CL15. |
| CL15 | 34 | Sandra Regol (EcoS) | Discussion commune | CL32 | Substitution de la qualification de transmission à l'alinéa 5 en concurrence avec CL32. |
| CL14 | 34 | Sandra Regol (EcoS) | Isolé | — | Suppression ciblée de l'alinéa 6 sans concurrent direct sur cette subdivision. |
| CL17 | 34 | Sandra Regol (EcoS) | Isolé | — | Insertion d'un droit à l'assistance d'un avocat après l'alinéa 7 sans concurrent direct. |
| CL30 | 34 | Élisa Martin (LFI-NFP) | Isolé | — | Suppression ciblée de l'alinéa 8 sans concurrent direct. |
| CL29 | APRÈS 34 | Jean-François Coulomme (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| CL27 | APRÈS 34 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| CL31 | APRÈS 34 | Jean-François Coulomme (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| CL7 | 35 | Marie-José Allemand (SOC) | Identique | CL18 | Chef de file d'amendements identiques (partagé avec CL18). |
| CL18 | 35 | Sandra Regol (EcoS) | Identique | CL7 | Dispositif rigoureusement identique déposé par un autre député. |
| CL22 | 35 | Paul Molac (LIOT) | Identique | CL7 | Dispositif rigoureusement identique déposé par un autre député. |
| CL42 | 35 | Émeline K/Bidi (GDR) | Identique | CL7 | Dispositif rigoureusement identique déposé par un autre député. |
| CL50 | 35 | Élisa Martin (LFI-NFP) | Identique | CL7 | Dispositif rigoureusement identique déposé par un autre député. |
| CL51 | 35 | Jean-François Coulomme (LFI-NFP) | Discussion commune | CL52 | Abrogation totale de l'article 10 de la loi JO 2024 en concurrence avec les réécritures partielles de CL52 et CL3. |
| CL52 | 35 | Jean-François Coulomme (LFI-NFP) | Discussion commune | CL51 | Interdiction de la biométrie et reconnaissance faciale en concurrence avec l'abrogation de CL51. |
| CL24 | 35 | Élisa Martin (LFI-NFP) | Discussion commune | CL3 | Interdiction de prolongation de la VSA au-delà de 2026 en concurrence avec l'expérimentation de CL3. |
| CL3 | 35 | Marie-José Allemand (SOC) | Discussion commune | CL51 | Limitation de l'expérimentation VSA à la seule durée des Jeux 2030 en concurrence avec CL51 et CL24. |
| CL53 | 35 | Jean-François Coulomme (LFI-NFP) | Discussion commune | CL3 | Encadrement des finalités de sécurité de la VSA en concurrence avec les régimes dérogatoires alternatifs. |
| CL44 | 35 | Jordan Guitton (RN) | Discussion commune | CL21 | Réécriture de l'alinéa 3 prolongeant la VSA jusqu'en 2027 en concurrence avec CL21 et CL45. |
| CL25 | 35 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| CL21 | 35 | Sandra Regol (EcoS) | Discussion commune | CL44 | Réécriture alternative de l'alinéa 3 encadrant le rapport d'évaluation en concurrence avec CL44. |
| CL45 | 35 | Jordan Guitton (RN) | Discussion commune | CL44 | Prolongation de l'expérimentation jusqu'au 31 décembre 2027 à l'alinéa 3 en concurrence avec CL44. |
| CL46 | 35 | Jordan Guitton (RN) | Discussion commune | CL44 | Insertion d'un a bis prolongeant les algorithmes après l'alinéa 3 en concurrence avec CL44. |
| CL26 | 35 | Élisa Martin (LFI-NFP) | Discussion commune | CL19 | Suppression de l'alinéa 4 en conflit direct avec les ajouts de garanties de CL19, CL54 et CL47. |
| CL19 | 35 | Sandra Regol (EcoS) | Discussion commune | CL54 | Interdiction expresse de la reconnaissance vocale après l'alinéa 4 en concurrence avec CL54 et CL47. |
| CL20 | 35 | Sandra Regol (EcoS) | Identique | AC170 | Chef de file d'amendements identiques (partagé avec AC170). |
| CL54 | 35 | Élisa Martin (LFI-NFP) | Discussion commune | CL19 | Exigence d'un arrêté préfectoral motivé après l'alinéa 4 en concurrence avec les garanties de CL19. |
| CL47 | 35 | Jordan Guitton (RN) | Discussion commune | CL19 | Rapport annuel de la CNIL après l'alinéa 4 en concurrence avec les verrous de CL19 et CL54. |
| CL55 | APRÈS 35 | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| CL28 | APRÈS 35 | Élisa Martin (LFI-NFP) | Discussion commune | CL37 | Rapport à 6 mois sur l'impact de la VSA sur les libertés publiques en concurrence avec CL37 et CL56. |
| CL37 | APRÈS 35 | Élisa Martin (LFI-NFP) | Discussion commune | CL28 | Rapport à 6 mois sur l'efficacité policière de la VSA en concurrence avec l'évaluation des libertés de CL28. |
| CL56 | APRÈS 35 | Élisa Martin (LFI-NFP) | Discussion commune | CL28 | Rapport d'évaluation à 5 ans de la VSA en concurrence avec les rapports semestriels de CL28 et CL37. |
| AC139 | APRÈS 35 | Joël Bruneau (LIOT) | Isolé | — | Amendement sans dispositif opérationnel. |
| CL60 | APRÈS 35 | Julien Rancoule (RN) | Isolé | — | Amendement sans dispositif opérationnel. |
| CD64 | 36 | Olga Givernet (EPR) | Identique | AC176 | Chef de file d'amendements identiques (partagé avec AC176). |
| CD66 | 36 | Olga Givernet (EPR) | Identique | AC177 | Chef de file d'amendements identiques (partagé avec AC177). |
| CD65 | 36 | Olga Givernet (EPR) | Identique | AC178 | Chef de file d'amendements identiques (partagé avec AC178). |
| AC90 | 3 BIS | Élisa Martin (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC101 | 3 BIS | Jean-François Coulomme (LFI-NFP) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC155 | 3 BIS | Olga Givernet (EPR) | Identique | CD60 | Dispositif rigoureusement identique déposé par un autre député. |
| AC156 | 3 BIS | Olga Givernet (EPR) | Identique | CD32 | Dispositif rigoureusement identique déposé par un autre député. |
| AC157 | 3 BIS | Olga Givernet (EPR) | Identique | CD16 | Dispositif rigoureusement identique déposé par un autre député. |
| AC158 | 3 BIS | Olga Givernet (EPR) | Identique | CD61 | Dispositif rigoureusement identique déposé par un autre député. |
| AC180 | 8 | Benjamin Dirx (EPR) | Identique | CF3 | Dispositif rigoureusement identique déposé par un autre député. |
| AC179 | APRÈS 8 | Benjamin Dirx (EPR) | Isolé | — | Modifie un point spécifique non contesté par les autres amendements de l'article APRÈS 8. |
| AC159 | 12 | Olga Givernet (EPR) | Identique | CD3 | Dispositif rigoureusement identique déposé par un autre député. |
| AC160 | 12 | Olga Givernet (EPR) | Identique | CD26 | Dispositif rigoureusement identique déposé par un autre député. |
| AC161 | 12 | Olga Givernet (EPR) | Identique | CD62 | Dispositif rigoureusement identique déposé par un autre député. |
| AC162 | 12 | Olga Givernet (EPR) | Identique | CD63 | Dispositif rigoureusement identique déposé par un autre député. |
| AC26 | 13 | Géraldine Bannier (Dem) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC143 | 13 | Romain Daubié (Dem) | Identique | CE21 | Dispositif rigoureusement identique déposé par un autre député. |
| AC144 | 17 | Romain Daubié (Dem) | Identique | CE22 | Dispositif rigoureusement identique déposé par un autre député. |
| AC145 | 18 | Romain Daubié (Dem) | Identique | CE23 | Dispositif rigoureusement identique déposé par un autre député. |
| AC163 | 18 BIS | Olga Givernet (EPR) | Identique | CD12 | Dispositif rigoureusement identique déposé par un autre député. |
| AC138 | 18 BIS | Joël Bruneau (LIOT) | Discussion commune | CD68 | Clause d'exclusion in fine concurrente encadrant la portée dérogatoire de l'article 18 BIS. |
| AC146 | 19 | Romain Daubié (Dem) | Identique | CE24 | Dispositif rigoureusement identique déposé par un autre député. |
| AC149 | 20 | Romain Daubié (Dem) | Identique | CE27 | Dispositif rigoureusement identique déposé par un autre député. |
| AC150 | 20 | Romain Daubié (Dem) | Identique | CE28 | Dispositif rigoureusement identique déposé par un autre député. |
| AC147 | 20 | Romain Daubié (Dem) | Identique | CE25 | Dispositif rigoureusement identique déposé par un autre député. |
| AC164 | 21 | Olga Givernet (EPR) | Isolé | — | Modifie un point spécifique non contesté par les autres amendements de l'article 21. |
| AC165 | APRÈS 21 | Olga Givernet (EPR) | Identique | CD42 | Dispositif rigoureusement identique déposé par un autre député. |
| AC166 | 22 | Olga Givernet (EPR) | Identique | CD54 | Dispositif rigoureusement identique déposé par un autre député. |
| AC167 | 22 | Olga Givernet (EPR) | Identique | CD55 | Dispositif rigoureusement identique déposé par un autre député. |
| AC168 | 22 | Olga Givernet (EPR) | Identique | CD30 | Dispositif rigoureusement identique déposé par un autre député. |
| AC169 | 22 | Olga Givernet (EPR) | Identique | CD56 | Dispositif rigoureusement identique déposé par un autre député. |
| AC171 | 22 | Olga Givernet (EPR) | Identique | CD57 | Dispositif rigoureusement identique déposé par un autre député. |
| AC172 | 22 | Olga Givernet (EPR) | Identique | CD58 | Dispositif rigoureusement identique déposé par un autre député. |
| AC173 | 22 | Olga Givernet (EPR) | Identique | CD59 | Dispositif rigoureusement identique déposé par un autre député. |
| AC174 | 22 | Olga Givernet (EPR) | Identique | CD44 | Dispositif rigoureusement identique déposé par un autre député. |
| AC127 | APRÈS 22 | Sébastien Peytavie (EcoS) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC175 | APRÈS 22 | Olga Givernet (EPR) | Identique | CD45 | Dispositif rigoureusement identique déposé par un autre député. |
| AC142 | 24 | Romain Daubié (Dem) | Identique | CE20 | Dispositif rigoureusement identique déposé par un autre député. |
| AC148 | 24 | Romain Daubié (Dem) | Identique | CE26 | Dispositif rigoureusement identique déposé par un autre député. |
| AC152 | 31 | Véronique Riotton (EPR) | Identique | CL2 | Dispositif rigoureusement identique déposé par un autre député. |
| AC153 | 31 | Véronique Riotton (EPR) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC151 | 31 | Véronique Riotton (EPR) | Isolé | — | Amendement sans dispositif opérationnel. |
| AC154 | 31 | Véronique Riotton (EPR) | Identique | CL10 | Dispositif rigoureusement identique déposé par un autre député. |
| AC170 | 35 | Véronique Riotton (EPR) | Identique | CL20 | Dispositif rigoureusement identique déposé par un autre député. |
| AC176 | 36 | Olga Givernet (EPR) | Identique | CD64 | Dispositif rigoureusement identique déposé par un autre député. |
| AC177 | 36 | Olga Givernet (EPR) | Identique | CD66 | Dispositif rigoureusement identique déposé par un autre député. |
| AC178 | 36 | Olga Givernet (EPR) | Identique | CD65 | Dispositif rigoureusement identique déposé par un autre député. |
