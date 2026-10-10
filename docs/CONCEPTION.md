# Conception du workflow `audit-dossier-btp`

Ce document explique **comment** le système fonctionne et **pourquoi** il a été construit ainsi.
Pour l'installer et le lancer, voir le [README](../README.md).

## 1. Le moteur réellement disponible (vérifié, pas supposé)

« Ultracode » est le mode d'orchestration par **workflows dynamiques** de Claude Code
(version examinée : 2.1.296). Ce qui a été vérifié dans le binaire puis sur le moteur réel :

| Point | Constat |
|---|---|
| Format | Script JavaScript (pas TypeScript) qui commence par `export const meta = {…}` littéral pur (`name`, `description`, `whenToUse`, `phases`). Taille max. 512 Ko. |
| Primitives | `agent(prompt, {label, phase, schema, effort, model, agentType, isolation})`, `parallel()` (barrière), `pipeline()` (sans barrière), `phase()`, `log()`, `args`, `budget`, `workflow()` (un niveau). |
| Résultats structurés | Avec `schema`, l'agent doit appeler un outil de sortie structurée, validé par le moteur (relance automatique si la forme est fausse). |
| Échecs | `agent()` renvoie `null` si l'agent meurt ou est ignoré ; `parallel()` ne rejette jamais (élément `null`). |
| Déterminisme | `Date.now()`, `new Date()` et `Math.random()` sont interdits (reprise par journal). |
| Script | Aucun accès fichier ni réseau : **seuls les agents** lisent, écrivent et exécutent. |
| Sous-agents | Type `workflow-subagent`, tous les outils sauf Agent et Workflow : ils peuvent lancer Python, lire et écrire. |
| Concurrence | min(16, CPU − 2) agents simultanés ; 1 000 agents au plus par exécution. |
| Enregistrement | Fichier `.js` dans `~/.claude/workflows/` (personnel, ou `$CLAUDE_CONFIG_DIR/workflows/`) ou `.claude/workflows/` (projet). Le nom de la commande est `meta.name`. |
| Invocation | `/audit-dossier-btp <texte>` : le texte arrive **tel quel, en chaîne** dans `args` (vérifié sur le moteur réel). |
| Activation | Réglage « Dynamic workflows » (`/config`) ou `"enableWorkflows": true` ; peut être interdit par l'organisation. |
| Communication entre agents | **Aucune primitive de messagerie entre agents.** Un agent ne peut ni appeler ni interroger un autre agent. |

Conséquence majeure : la communication entre spécialistes ne peut pas être « simulée » par un agent
qui raconterait un dialogue. Elle est **médiée par le script** : questions écrites dans des fichiers,
routées par du code, réponses écrites par le destinataire, statuts recalculés par du code.

## 2. Architecture

```
                 ┌──────────────────────── script = coordinateur (déterministe) ────────────────────────┐
 Phase 0-2       │ opérateur d'outils : preflight.py → inventaire.py (empreintes, extraction, versions,  │
                 │ références, normes, consignes suspectes)  →  documentaliste (classement, pièces       │
                 │ manquantes, pièces quantitatives, rapprochements utiles, sujets hors chartes)         │
 Phase 3         │ RÈGLES EXPLICITES d'activation des agents (+ plafonds du mode, + budget)              │
                 │ contrôles amont déterministes : dpgf_check.py, rapprochement.py, ifc_probe.py         │
 Phase 4         │ spécialistes en parallèle, lecture indépendante → constats/<agent>.json validés       │
 Phase 5         │ registre.py build (preuves, citations, statuts) → réparation des fichiers invalides   │
                 │ → juge de dédoublonnage (paires candidates repérées par code)                         │
 Phase 6         │ synthèse inter-lots + OPC (lisent le registre) → registre.py transmissions (routage)  │
                 │ → réponses des destinataires (confirme / réfute / nuance / non résolu, corrections,   │
                 │ retraits) → tour 2 en mode approfondi → 2e passage du juge de dédoublonnage           │
 Phase 7         │ registre.py selection → vérificateurs à lentilles distinctes (pipeline par constat)   │
                 │ → arbitre seulement en cas de désaccord                                               │
 Phase 8-9       │ critique de complétude (approche inverse) → vérification des nouveaux constats        │
                 │ → boucle bornée, arrêt dès qu'une passe ne trouve rien                                │
 Phase 10        │ rédacteur (synthèse depuis le registre seul) → livrables.py → controle_qualite.py     │
 Phase 11        │ revue qualité (agent) → correction bornée → porte qualité finale                      │
                 └──────────────────────────────────────────────────────────────────────────────────────┘
```

### Agents et chartes

| Clé | Rôle | Activé quand |
|---|---|---|
| `documentaliste` | gestion documentaire, cadrage | toujours |
| `economie` | DPGF, DQE, BPU, cohérence économique | pièce quantitative présente |
| `metres` | logique des quantités | pièce quantitative + source dimensionnelle |
| `cctp` | pièces écrites contractuelles | CCTP, CCAP ou notice présents |
| `architecture`, `structure_go`, `enveloppe`, `interieur`, `cvc_plomberie`, `electricite` | disciplines | au moins une pièce exploitable de la discipline |
| `bim` | maquettes IFC | fichier IFC présent (un RVT seul est déclaré illisible, sans lancer d'agent) |
| `references` | références techniques et réglementaires | mode standard/approfondi et normes citées (ou `web=oui`) |
| `dyn_*` | spécialiste créé pour un sujet hors chartes (VRD, ascenseur…) | proposé par le documentaliste, 0/2/4 selon le mode |
| `synthese_interlots`, `opc` | second ordre, lisent le registre | ≥ 2 lots et ≥ 2 spécialistes ; OPC hors mode rapide ou si un planning existe |
| juge de dédoublonnage, vérificateurs, arbitre, critique de complétude, rédacteur, revue qualité | contrôle | selon les phases |

Chaque charte (dans le script, objet `CHARTES`) contient les 12 éléments demandés : mission, questions,
pièces prioritaires (calculées depuis le classement), outils réellement disponibles, périmètre,
sujets laissés aux autres, éléments à transmettre, preuves exigées, erreurs typiques, **interdits**,
conditions d'analyse impossible, critères de fin. Les règles communes (sécurité, interdiction
d'inventer, absence ≠ omission, hiérarchie documentaire, grille de qualification) sont injectées
dans tous les prompts.

## 3. Ce qui a été changé par rapport au cahier des charges, et pourquoi

| Proposition initiale | Problème | Solution retenue | Bénéfice |
|---|---|---|---|
| Un agent coordinateur central qui supervise tout | Un agent n'existe que le temps d'une tâche ; il ne peut ni lancer ni attendre d'autres agents | Le **script** est le coordinateur (ordre, parallélisme, routage, relances, arbitrages déclenchés par règle) ; le jugement est confié à des agents ponctuels | Contrôle déterministe, rejouable, sans « coordinateur » qui résume à sa façon |
| Agents qui se parlent | Aucune primitive de messagerie | Protocole par fichiers : `transmissions` → routage par `registre.py` (doublons, destinataires inactifs, questions voisines sur un même constat regroupées, questions à un co-auteur du constat écartées, plafonds journalisés) → `echanges/rN/<agent>.json` → statuts recalculés | Échanges réels et traçables, jamais un dialogue simulé ; le quota de questions sert aux réponses indépendantes |
| Un agent DPGF qui vérifie les calculs | Un modèle peut se tromper en arithmétique | `dpgf_check.py` et `rapprochement.py` calculent ; l'agent interprète (forfaits, lignes à chiffrer par les entreprises) | Erreurs arithmétiques prouvées, non estimées |
| Statuts attribués par les agents | Un agent peut se déclarer « corroboré » | Les statuts sont **calculés** par `registre.py` à partir des verdicts, des échanges, des contrôles et des arbitrages | Pas d'auto-validation |
| Vérification par un agent sceptique | Un seul relecteur a un angle mort | Vérificateurs à **lentilles distinctes** (provenance, calcul, interprétation), nombre selon gravité et mode ; une réfutation par un seul pair est elle-même contrôlée | Diversité des angles d'attaque |
| Citer les sources | Une citation peut être inventée | Chaque citation est **recherchée mot pour mot** dans l'extrait de la pièce ; introuvable ⇒ confiance abaissée, constat éventuellement requalifié | Lutte directe contre les références fabriquées |
| Un agent réglementation | Risque d'inventer DTU et articles | Agent limité aux références citées par le dossier ; web seulement si `web=oui` ; la porte qualité signale toute norme mentionnée par un agent qui n'est ni dans le dossier ni sourcée | Pas de norme « de mémoire » présentée comme vérifiée |
| 18 agents systématiques | Coût sans valeur si les pièces manquent | Activation par **règles explicites** sur le classement, plafonds par mode, réduction de périmètre selon le budget, tout ce qui est écarté est journalisé | Proportionnalité, aucune troncature silencieuse |
| Fusion des doublons | Fusionner sur la forme fait perdre des constats distincts | Paires candidates repérées par code ; un juge décide (même preuve + même ouvrage + même action) ; fusion automatique seulement si même contrôle déterministe | Fusion prudente ; une détection par deux agents compte comme corroboration |
| Rapport rédigé librement | Sur-affirmation possible | Rapport **généré par code** depuis le registre ; seule la synthèse est rédigée, puis contrôlée (Q04, Q05) et corrigée une fois au besoin | Livrables cohérents entre eux, statuts toujours visibles |
| — (non demandé) | Les documents peuvent contenir des instructions adressées à une IA | Détection par motifs à l'inventaire, règle « données ≠ instructions », constat obligatoire | Résistance à l'injection de consignes |

## 4. Contrat de données

Schémas dans `audit-dossier-btp/schemas/` (validés par `registre.py validate`, utilisés par la porte qualité) :
`constats` (fichier d'un agent : constats, transmissions, documents examinés, RAS, limites),
`reponses` (tour d'échanges : verdicts, corrections, retraits), `verification`, `arbitrage`,
`fusions`, `classement`, `synthese`, `revue`.

Un constat porte les champs demandés (`finding_id`, `title`, `discipline`, `lot`, `finding_type`,
`severity`, `priority`, `status`, `confidence`, `claim`, `evidence`, `sources`, `calculation`,
`economic_impact`, `technical_impact`, `dependencies`, `counterarguments`, `recommended_action`,
`responsible_party`, `open_questions`) plus `severity_criteria`, `severity_rationale`,
`confidence_rationale`, `decision_deadline`. Le registre ajoute : `evidence_level`, `quality_flags`,
`origin_agents`, `merged_from`, `echanges`, `verifications`, `arbitrage`, `motif_statut`,
`finding_type_initial`, `confidence_initiale`.

### Règles de statut (dans l'ordre, `registre.py`)

1. retrait par l'auteur → `refute`
2. arbitrage : maintenu → `corrobore`, rejeté → `refute`, requalifié ou désaccord → `non_resolu` ;
   maintenu ou rejeté **sans élément décisif** → `non_resolu`
3. confirmations **et** réfutations → `conteste` (arbitrage déclenché)
4. réfutations seules → `refute`
5. verdicts « preuve insuffisante » ≥ confirmations → `non_resolu`, requalifié en question ouverte
6. confirmations (vérificateur, pair **indépendant**, contrôle déterministe) → `corrobore`
7. détection par au moins deux agents → `corrobore`
8. sinon → `a_verifier`

Un pair n'est indépendant que s'il n'est pas auteur du constat (y compris après fusion).

### Niveau de preuve et requalification

`prouve_par_outil` (identifiant de contrôle retrouvé et valeurs concordantes) >
`citation_verifiee` > `observation_localisee` > `non_etaye`. Une « anomalie avérée » sans
contrôle ni citation vérifiée et avec une seule source est requalifiée en « incohérence » ;
non étayée, elle devient une « question ouverte ».

## 5. Grille de qualification

- **Gravité** (conséquence si vrai, critères explicites) : critique, majeure, modérée, mineure.
- **Priorité** (urgence de décision) : P1 avant l'étape suivante du projet, P2 avant l'exécution de
  l'ouvrage, P3 à suivre.
- **Confiance** (solidité de la preuve) : élevée, moyenne, faible.

Pas de note unique : la gravité, la priorité et la confiance restent séparées et justifiées.

## 6. Coûts, échecs et reprise

- Modes : `rapide` (≈ 20-30 agents), `standard` (≈ 40-60), `approfondi` (≈ 60-120) selon le dossier.
- Durée : le moteur exécute au plus min(16, nombre de cœurs − 2) agents à la fois ; sur un poste à
  4 cœurs, seulement 2 agents travaillent simultanément.
- Relance unique d'un spécialiste sans résultat ou à fichier non validé ; réparation unique d'un
  fichier rejeté par le registre ; divergences entre l'index annoncé et le fichier écrit journalisées.
- Budget (si l'utilisateur fixe une cible « +500k ») : réserve pour la rédaction et les livrables,
  réduction du nombre de spécialistes, plafond de vérification, phases facultatives abandonnées
  en premier ; chaque réduction est inscrite dans les limites du rapport.
- Reprise : le moteur rejoue les appels d'agents inchangés (`resumeFromRunId`) ; le registre étant
  reconstruit à partir des fichiers, une reprise ne crée pas d'état incohérent.
- Si les livrables ne peuvent pas être produits, le résultat du workflow donne la commande exacte
  pour les régénérer à partir de `_travail/`.

## 7. Améliorations envisagées (non implémentées)

- Mode « reprise ciblée » : relancer seulement un lot ou un constat sur un dossier déjà audité.
- Lecture géométrique des IFC (ifcopenshell) pour comparer quantités calculées et déclarées.
- Lecture des DWG/DXF (textes et cotes) via un convertisseur, si l'utilisateur en installe un.
- Bibliothèque de prix datée et sourcée fournie par l'utilisateur, pour valoriser les écarts hors PU du dossier.
- Comparaison de deux versions d'un même dossier (ce qui a changé entre indices).
- Calibration : mesurer sur plusieurs dossiers réels annotés le taux de constats confirmés par un professionnel.
