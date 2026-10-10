# workflow-BTP — `audit-dossier-btp`

Workflow multi-agents pour Claude Code (mode **Ultracode** / workflows dynamiques) qui audite un
dossier de construction : pièces écrites (CCTP, CCAP), pièces économiques (DPGF, DQE, BPU),
métrés, plans, coupes, détails et maquettes IFC.

Il produit des constats **tracés jusqu'à la pièce source**, fait **échanger** les spécialistes entre
eux, soumet les constats importants à une **vérification contradictoire**, cherche ce qui a été
**oublié**, puis génère des livrables exploitables (rapport, registre CSV/Excel, rapprochement
économique, questions à arbitrer, risques et interfaces, manifeste et journal des contrôles).

> C'est une aide à l'analyse. Elle ne remplace ni un professionnel qualifié, ni une note de calcul,
> ni un contrôle réglementaire. Chaque constat affiche son statut de vérification.

## Installation (espace personnel, pour tous vos projets)

Prérequis : Claude Code 2.1 ou plus récent avec les workflows dynamiques autorisés, Python 3.9+.

```bash
git clone https://github.com/niswbrrr/workflow-BTP.git
cd workflow-BTP
python install.py                 # copie dans ~/.claude (ou $CLAUDE_CONFIG_DIR)
```

- Si une autre version existe, rien n'est remplacé ; `--forcer` la remplace en gardant une sauvegarde.
- Activez les workflows dynamiques : `/config` → « Dynamic workflows », ou `python install.py --activer-workflows`
  (ajoute `"enableWorkflows": true` à `~/.claude/settings.json` avec sauvegarde). Une organisation
  peut interdire cette fonction ; dans ce cas, seul l'administrateur peut l'autoriser.
- Bibliothèques Python **facultatives** mais recommandées (à installer vous-même) :
  `pip install --user pdfplumber openpyxl python-docx`. Sans elles, le workflow fonctionne en mode
  dégradé et le dit dans ses limites (texte des PDF non extrait, citations PDF non vérifiables).
- Vérifier une installation : `python install.py --verifier`.

Le dépôt contient aussi `.claude/workflows/audit-dossier-btp.js` : dans une session ouverte sur ce
dépôt (y compris Claude Code sur le web), la commande est disponible sans installation.

## Utilisation

Dans n'importe quelle session Claude Code :

```
/audit-dossier-btp "C:\Users\moi\Documents\Dossier DCE" mode=standard
/audit-dossier-btp ./dossiers/ecole mode=rapide perimetre="lots 02 et 03" phase=DCE
/audit-dossier-btp ./dossiers/ecole mode=approfondi sortie=./audits/ecole web=oui
```

| Option | Valeurs | Effet |
|---|---|---|
| (premier argument) | chemin | dossier à analyser (lecture seule) ; guillemets si le chemin contient des espaces |
| `mode=` | `rapide`, `standard` (défaut), `approfondi` | nombre d'agents, de vérificateurs, de tours d'échanges et de passes de complétude |
| `sortie=` | chemin | répertoire de sortie (défaut `./livrables_audit` ; jamais écrasé : `-2`, `-3`… si existant) |
| `perimetre=` | texte | concentre l'analyse (les sujets importants hors périmètre sont signalés) |
| `phase=` | DCE, ACT, EXE… | aide à fixer les priorités |
| `web=oui` | — | autorise l'agent « références » à consulter des sources officielles (requêtes génériques, aucun contenu du dossier envoyé) |
| `outils=` | chemin | emplacement des outils si non standard |

Vous pouvez fixer un budget de jetons dans votre message (par exemple `+500k`) : le workflow réduit
alors son périmètre en conséquence et le déclare dans les limites du rapport.

| Mode | Spécialistes techniques | Vérificateurs (critique / majeure / modérée) | Tours d'échanges | Complétude | Ordre de grandeur |
|---|---|---|---|---|---|
| rapide | 2 au plus (+ économie, métrés, CCTP) | 1 / 1 / 0 | 1 | déterministe seulement | 20-30 agents |
| standard | 8 au plus | 3 / 2 / 1 si P1 ou chiffré | 1 | 1 passe | 40-60 agents |
| approfondi | 12 au plus | 3 / 3 / 2 | 2 | 2 passes | 60-120 agents |

### Livrables (`livrables_audit/`)

| Fichier | Contenu |
|---|---|
| `rapport_audit_dossier_btp.md` | synthèse, périmètre, limites, constats établis, à vérifier, désaccords, risques économiques, interfaces, réfutés, recommandations, contrôle qualité |
| `registre_anomalies.csv` (+ `.xlsx`) | une ligne par constat, tous les champs, séparateur `;`, ouvrable dans Excel FR |
| `rapprochement_economique.csv` | écarts de quantités entre pièces et contrôles arithmétiques, avec constats liés |
| `questions_a_arbitrer.md` | questions par destinataire, avec contexte, pièces et raison |
| `risques_et_interfaces.md` | interfaces entre lots, dépendances, décisions et échéances |
| `manifeste_documentaire.csv` | chaque pièce : format, extraction, type, lots, indice, exploitation, agents qui l'ont examinée |
| `journal_controles.md` | outils exécutés, agents lancés et leur résultat, plan, limites, fichiers rejetés |
| `_travail/` | toutes les traces : extraits, contrôles, constats par agent, échanges, vérifications, arbitrages, registre |

Statuts : **corroboré** (confirmé par un vérificateur, un pair indépendant ou un contrôle
déterministe) · **à vérifier** (un seul agent) · **contesté** · **non résolu** (désaccord persistant
ou preuve insuffisante) · **réfuté**. Seuls les constats corroborés figurent dans « constats établis ».

## Comment ça marche (résumé)

1. **Environnement et inventaire** — Python et outils localisés, répertoire de sortie neuf,
   inventaire avec empreintes, doublons, familles d'indices, références citées absentes, normes
   citées, consignes suspectes adressées à une IA, extraction du texte page par page.
2. **Cadrage documentaire** — un agent classe chaque pièce sans décider quelle version s'applique.
3. **Planification** — des règles explicites choisissent les agents ; les contrôles déterministes
   (arithmétique DPGF, rapprochement métré/DPGF, sonde IFC) tournent avant les spécialistes.
4. **Collecte** — chaque spécialiste analyse seul, selon sa charte, et écrit un fichier validé.
5. **Consolidation** — registre reconstruit par code : vérification des citations mot pour mot,
   recalcul des formules, niveau de preuve, fusion des doublons décidée par un juge.
6. **Échanges** — la synthèse inter-lots et l'OPC posent des questions ; le script les route vers
   le bon spécialiste, qui confirme, réfute, nuance, corrige ou retire.
7. **Vérification contradictoire** — vérificateurs à lentilles différentes ; arbitre seulement en
   cas de désaccord ; un désaccord sans élément décisif reste visible.
8. **Complétude** — un critique repart des pièces pour trouver ce qui manque ; boucle bornée.
9. **Livrables** — générés par code depuis le registre ; synthèse rédigée puis contrôlée.
10. **Contrôle final** — porte qualité automatique (12 contrôles) et revue, correction bornée.

Détails, justification des choix et règles de statut : [docs/CONCEPTION.md](docs/CONCEPTION.md).
Résultats des essais : [docs/ESSAIS.md](docs/ESSAIS.md).

## Tests

```bash
python3 -m unittest discover -s tests -p "test_*.py"   # outils déterministes (bibliothèque standard)
npm install --prefix tests                            # une fois : acorn et ajv pour les tests JS
node tests/valider_workflow.mjs                        # validation statique selon les règles du moteur
node tests/test_e2e_simule.mjs                         # bout en bout simulé : vrai script, vrais outils, agents scriptés
python3 tests/fabriquer_dossier_test.py                # régénère le dossier d'essai (reportlab, openpyxl, python-docx)
```

Le dossier `tests/dossier_test/` est un projet **entièrement fictif** qui contient des pièges
connus (erreur arithmétique, écart métré/DPGF, détail manquant, plan remplacé, interface de
réservations, désaccord d'épaisseur de dalle, consigne piégée adressée à une IA, doublon de fichier).

## Sécurité

Lecture seule sur les pièces d'origine ; écriture uniquement dans le répertoire de sortie ; aucun
envoi de pièce à un service externe ; aucune exécution de script provenant du dossier ; les consignes
trouvées dans les documents sont traitées comme des données et signalées ; aucune configuration
globale modifiée sans l'option explicite `--activer-workflows`.

## Structure du dépôt

```
.claude/workflows/audit-dossier-btp.js   le workflow (orchestrateur, chartes, protocole)
audit-dossier-btp/tools/                 outils déterministes Python (bibliothèque standard d'abord)
audit-dossier-btp/schemas/               contrat de données (JSON Schema)
install.py                               installation personnelle
docs/                                    conception et résultats des essais
tests/                                   dossier d'essai, scénario simulé, validateur, runtime simulé
```
