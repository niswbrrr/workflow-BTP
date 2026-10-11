# État du projet `workflow-BTP`

État constaté le **2026-10-11 vers 00:40 UTC**, sur le commit `c9311af` de `main`. Ce document
distingue ce qui est **vérifié** (avec la nature de la vérification) de ce qui est seulement
**conçu ou prévu**. Une fonctionnalité discutée ou demandée n'est jamais présentée comme
opérationnelle sans preuve. Historique détaillé de la dernière heure de travail :
[docs/journaux/2026-10-11-reconstitution-session-claude.md](journaux/2026-10-11-reconstitution-session-claude.md).

Niveaux de vérification :

- **réel** : exécuté par Claude Code 2.1.296 avec de vrais agents ;
- **simulé** : le vrai script et les vrais outils Python, exécutés avec des agents scriptés
  (`tests/test_e2e_simule.mjs`) ;
- **unitaire** : `tests/test_outils.py` ;
- **statique** : `tests/valider_workflow.mjs`.

## 1. Objectif

Fournir un workflow multi-agents pour Claude Code (workflows dynamiques, dits « Ultracode »),
`audit-dossier-btp`, qui audite un dossier de construction : CCTP, CCAP, DPGF/DQE/BPU, métrés,
plans, IFC. Il produit :

- des constats tracés jusqu'aux pièces ;
- des échanges entre spécialistes ;
- une vérification contradictoire ;
- une critique de complétude ;
- des livrables générés par code (rapport, registre CSV/Excel, rapprochement économique, questions
  à arbitrer, risques et interfaces, manifeste, journal des contrôles).

Public visé : économie de la construction (le projet est réalisé dans le cadre d'un BTS). L'outil
aide à l'analyse ; il ne remplace ni un professionnel ni un contrôle réglementaire.

## 2. Structure réelle (fichiers suivis par Git : 56)

```
.claude-plugin/plugin.json, marketplace.json   plugin « btp » 1.0.0, marketplace « workflow-btp »
.claude/workflows/audit-dossier-btp.js         orchestrateur (1 184 lignes)
audit-dossier-btp/tools/   9 fichiers Python   btp_common, preflight, inventaire, dpgf_check,
                                               rapprochement, ifc_probe, registre, livrables,
                                               controle_qualite (3 506 lignes au total)
audit-dossier-btp/schemas/ 8 schémas JSON      classement, constats, fusions, reponses, verification,
                                               arbitrage, synthese, revue
install.py                                     installation personnelle (~/.claude ou $CLAUDE_CONFIG_DIR)
docs/CONCEPTION.md, docs/ESSAIS.md             conception motivée ; résultats des essais
docs/exemple_livrables/    8 fichiers          livrables réels de l'essai n° 2 (projet fictif)
tests/                     23 fichiers         dossier fictif piégé (12 pièces), tests unitaires,
                                               validateur, runtime simulé, scénario, essai réel
README.md
```

Ajoutés par la reconstitution du 2026-10-11 : `docs/journaux/` (journal et annexes),
`scripts/journal/` (deux scripts d'extraction) et ce fichier.

## 3. Composants et état de vérification

| Composant | Rôle | Vérification |
|---|---|---|
| Workflow `audit-dossier-btp.js` | 10 phases déclarées ; 13 chartes de spécialistes et des rôles ponctuels (documentaliste, juge de fusion, vérificateurs, arbitre, critique de complétude, rédacteur, revue) ; protocole d'échanges médié par le script ; modes rapide, standard et approfondi | statique ✔ ; simulé ✔ (5 scénarios, 85 vérifications) ; **réel ✔ en mode rapide uniquement** (essai n° 2 complet) |
| Outils Python | Inventaire, extraction, contrôles DPGF, rapprochement, sonde IFC, registre et statuts, livrables, porte qualité (12 contrôles) | unitaire ✔ (14 tests) ; utilisés par les essais réels |
| Contrat de données (schémas) | Validation des fichiers écrits par les agents | simulé ✔ ; réel ✔ (0 fichier rejeté sur 2 essais) |
| `install.py` | Copie non destructive dans l'espace personnel, `--forcer` avec sauvegarde, `--activer-workflows`, `--verifier` | essai sur une cible temporaire ✔ ; installation réelle dans le conteneur et lancement depuis un projet vide ✔ |
| Plugin `btp` et marketplace `workflow-btp` | Installation depuis l'onglet Plugins ; commande `/btp:audit-dossier-btp` | `claude plugin validate --strict` ✔. Installation depuis GitHub (branche) et lancement du workflow ✔. Installation depuis `main` ✔ (présence des fichiers seulement). |
| Tests (`tests/`) | Régression | les 3 suites passent sur `c9311af` (relancées le 2026-10-11) |
| Scripts `scripts/journal/` | Reconstitution d'une session à partir de sa transcription | utilisés pour produire les annexes du journal |

## 4. Fonctionnalités vérifiées

| Fonctionnalité | Niveau | Preuve |
|---|---|---|
| Inventaire, empreintes, doublons, familles d'indices, références citées absentes, consignes suspectes adressées à une IA | unitaire, simulé, réel | `docs/ESSAIS.md` § 1, 3 et 4.2 |
| Classement documentaire sans trancher les versions | réel | ESSAIS § 4.2 |
| Contrôles arithmétiques DPGF, rapprochement métré/DPGF, sonde IFC | unitaire, réel | ESSAIS § 1 et 4.4 |
| Citations vérifiées mot pour mot, formules recalculées | unitaire, réel (toutes les citations retrouvées ; plus aucune formule non recalculable dans l'essai n° 2) | ESSAIS § 4.4 |
| Dédoublonnage par un juge, refus motivés | réel | ESSAIS § 4.2 et 4.4 |
| Échanges routés : regroupement par constat, exclusion des co-auteurs, plafond par destinataire | réel (1 tour) | journal, C50 |
| Vérification contradictoire | réel (10 constats, 6 confirmés, 4 à reformuler) | ESSAIS § 4.4 |
| Livrables et porte qualité | réel (8 fichiers, verdict « conforme avec réserves », 0 erreur) | `docs/exemple_livrables/` |
| Reconstruction du registre avant la rédaction | **simulé seulement** (un test de non-régression échoue bien sur l'ancienne version) | journal, C55 et C56 |
| Questions regroupées en 6 rôles de destinataires | régénération des livrables de l'essai n° 2 (sans nouvel essai) | journal, C57 |
| Arrêt propre si le dossier est introuvable ou les arguments absents | simulé ; réel (installation personnelle et plugin) | ESSAIS § 3, 4.3 et 4.5 |
| Panne d'agent avec relance unique ; réduction de périmètre sous budget | **simulé seulement** | ESSAIS § 3 |

## 5. Conçu mais non éprouvé avec de vrais agents

- Modes **standard** et **approfondi** : OPC, références (`web=oui`), critique de complétude par
  agent, revue qualité finale, second tour d'échanges, arbitrage.
- Réfutation d'un constat (piège S4) et désaccord persistant (piège S7) : vus en simulation
  seulement.
- Dossiers réels volumineux, PDF scannés (sans couche texte), postes Windows.
- Exécution du workflow depuis une installation du plugin faite depuis `main`. Elle a été faite
  depuis la branche, avec un script identique.

## 6. Dépendances et configuration

| Élément | Exigence | Remarque |
|---|---|---|
| Claude Code | workflows dynamiques activés (`/config` → « Dynamic workflows », ou `"enableWorkflows": true`) | essais faits avec la version 2.1.296. Une organisation peut interdire cette fonction. |
| Python | 3.9 ou plus, bibliothèque standard | `pdfplumber`, `openpyxl` et `python-docx` sont facultatifs. Sans eux, le mode est dégradé et déclaré dans les limites du rapport. |
| Node.js et `acorn`, `ajv` | tests JavaScript seulement | `npm install --prefix tests` |
| `reportlab`, `openpyxl`, `python-docx` | régénération du dossier d'essai seulement | `tests/fabriquer_dossier_test.py` |
| Variables d'environnement pour `claude -p` | `CLAUDE_CODE_WORKFLOWS=1` ; `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` pour qu'un essai non interactif ne soit pas arrêté après 10 minutes | déjà dans `tests/lancer_essai_reel.sh` |
| Concurrence | le moteur fait travailler au plus min(16, cœurs − 2) agents à la fois | 2 sur un poste à 4 cœurs : l'essai n° 2 a duré 15 minutes |
| Coût observé | essai réel en mode rapide sur 12 pièces : environ 5 $ | ESSAIS § 4.4 |

## 7. Problèmes ouverts

1. **Aucune intégration continue.** La PR #1 n'avait aucune vérification automatique : les tests ne
   tournent que s'ils sont lancés à la main.
2. **Dernières corrections non éprouvées en réel** : reconstruction du registre avant la rédaction,
   rôles de destinataires.
3. **Écarts de documentation** relevés par la reconstitution (non corrigés, pour ne pas modifier
   les fichiers existants dans cette mission) :
   - `docs/ESSAIS.md` § 4.4 n'indique pas les 10 transmissions écartées par le plafond de 3 sujets
     par destinataire ;
   - le coût du § 4.3 n'inclut pas un premier appel sans argument (0,056 $) ;
   - la note du `README.md` sur l'installation depuis la branche de la PR est sans objet depuis la
     fusion ;
   - le message du commit `f008fa9` cite des corrections déjà incluses dans `625c22a`.
4. **Taille du plugin.** Le plugin embarque tout le dépôt (`source: "./"`), dossier d'essai et
   documentation compris (environ 1 Mo).
5. **Recherche des outils dans le cache des plugins.** Le workflow prend le `preflight.py` le plus
   récent sous `~/.claude/plugins`. Si plusieurs versions coexistent dans le cache, ce choix repose
   sur la date des fichiers : comportement non éprouvé avec deux versions installées.

## 8. Prochaines étapes recommandées

1. Ajouter une CI (GitHub Actions) qui lance les trois suites de tests sur chaque PR. Elles
   tournent en moins d'une minute et sans jeton.
2. Faire un essai réel en **mode standard** (`tests/lancer_essai_reel.sh standard`). Il éprouve en
   même temps les dernières corrections et les phases jamais exécutées en réel (OPC, complétude,
   revue, arbitrage). À prévoir : un coût supérieur à celui du mode rapide.
3. Corriger les écarts de documentation listés au point 7.3.
4. Essayer le plugin sur un poste Windows et sur un vrai dossier de chantier, avec des PDF scannés.
5. Envisager un plugin allégé (sans `tests/` ni `docs/exemple_livrables/`), en gardant la
   validation `claude plugin validate --strict`.
