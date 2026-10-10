# Journal des contrôles et de l'exécution

## Outils déterministes exécutés

| Horodatage | Outil | Statut | Détails |
|---|---|---|---|
| 2026-10-10T23:28:34+00:00 | preflight | ok | {"source": "/home/user/workflow-BTP/tests/dossier_test", "sortie": "<essai>/livrables_audit", "capacites": {"pdf_texte": "pdfplumber", "xlsx": "openpyxl", "docx": "python-docx", "ifc": "stdlib (lecture STEP partielle |
| 2026-10-10T23:28:36+00:00 | inventaire | ok | {"nb_documents": 12, "par_extraction": {"texte_extrait": 8, "tableur_extrait": 3, "maquette_ifc": 1}, "doublons_exacts": 1, "familles_versions": 1, "consignes_suspectes": 1} |
| 2026-10-10T23:29:29+00:00 | dpgf_check | ok | {"fichier": "/home/user/workflow-BTP/tests/dossier_test/02_Pieces_economiques/DPGF_Lot02_Gros_oeuvre.xlsx", "doc_id": "D005", "controles_par_type": {"ARITH": 1}} |
| 2026-10-10T23:29:30+00:00 | dpgf_check | ok | {"fichier": "/home/user/workflow-BTP/tests/dossier_test/02_Pieces_economiques/DPGF_Lot03_Facades.xlsx", "doc_id": "D006", "controles_par_type": {}} |
| 2026-10-10T23:29:31+00:00 | dpgf_check | partiel | {"fichier": "/home/user/workflow-BTP/tests/dossier_test/03_Metres/Metre_Facades.xlsx", "doc_id": "D007", "controles_par_type": {}} |
| 2026-10-10T23:29:32+00:00 | rapprochement | partiel | {"a": "D007", "b": "D006", "par_statut": {"concordant": 2, "ecart": 1, "absent_de_metre": 1}} |
| 2026-10-10T23:34:20+00:00 | registre.build | ok | {"nb_constats": 39, "par_statut": {"a_verifier": 37, "corrobore": 2}, "par_type": {"incoherence": 11, "omission_possible": 6, "question_ouverte": 16, "anomalie_averee": 1, "risque": 5}, "par_gravite": {"critique": 2, "majeure": 17, "moderee": 15, "mineure": 5}, "fichiers_invalides": 0} |
| 2026-10-10T23:35:08+00:00 | registre.build | ok | {"nb_constats": 24, "par_statut": {"corrobore": 9, "a_verifier": 15}, "par_type": {"incoherence": 6, "omission_possible": 6, "question_ouverte": 10, "anomalie_averee": 1, "risque": 1}, "par_gravite": {"critique": 2, "majeure": 10, "moderee": 11, "mineure": 1}, "fichiers_invalides": 0} |
| 2026-10-10T23:36:44+00:00 | registre.build | ok | {"nb_constats": 28, "par_statut": {"corrobore": 9, "a_verifier": 19}, "par_type": {"incoherence": 7, "omission_possible": 7, "question_ouverte": 12, "anomalie_averee": 1, "risque": 1}, "par_gravite": {"critique": 3, "majeure": 13, "moderee": 11, "mineure": 1}, "fichiers_invalides": 0} |
| 2026-10-10T23:36:45+00:00 | registre.transmissions | ok | {"round": 1, "destinataires": {"architecture": 3, "cctp": 3, "economie": 3, "enveloppe": 3, "metres": 3, "synthese_interlots": 2}, "ecartees": 26} |
| 2026-10-10T23:40:20+00:00 | registre.build | ok | {"nb_constats": 28, "par_statut": {"corrobore": 13, "a_verifier": 15}, "par_type": {"incoherence": 7, "omission_possible": 7, "question_ouverte": 12, "anomalie_averee": 1, "risque": 1}, "par_gravite": {"critique": 3, "majeure": 13, "moderee": 11, "mineure": 1}, "fichiers_invalides": 0} |
| 2026-10-10T23:40:27+00:00 | registre.build | ok | {"nb_constats": 28, "par_statut": {"corrobore": 13, "a_verifier": 15}, "par_type": {"incoherence": 7, "omission_possible": 7, "question_ouverte": 12, "anomalie_averee": 1, "risque": 1}, "par_gravite": {"critique": 3, "majeure": 13, "moderee": 11, "mineure": 1}, "fichiers_invalides": 0} |
| 2026-10-10T23:40:27+00:00 | registre.selection | ok | {"mode": "rapide", "selection": 10, "plafond_depasse": 6} |
| 2026-10-10T23:43:36+00:00 | registre.build | ok | {"nb_constats": 28, "par_statut": {"corrobore": 16, "a_verifier": 12}, "par_type": {"incoherence": 7, "omission_possible": 7, "question_ouverte": 12, "anomalie_averee": 1, "risque": 1}, "par_gravite": {"critique": 3, "majeure": 13, "moderee": 11, "mineure": 1}, "fichiers_invalides": 0} |
| 2026-10-10T23:43:38+00:00 | livrables | ok | {"fichiers": ["registre_anomalies.csv", "rapprochement_economique.csv", "manifeste_documentaire.csv", "questions_a_arbitrer.md", "risques_et_interfaces.md", "journal_controles.md", "rapport_audit_dossier_btp.md", "registre_anomalies.xlsx"]} |
| 2026-10-10T23:43:39+00:00 | controle_qualite | conforme_avec_reserves | {"erreurs": 0, "avertissements": 9} |

## Agents lancés par le workflow

| Agent | Phase | Résultat | Remarque |
|---|---|---|---|
| outil:environnement | Environnement et inventaire | ok |  |
| documentaliste | Cadrage documentaire | ok |  |
| outil:controles-amont | Planification et contrôles amont | ok |  |
| spec:economie | Collecte spécialisée | ok |  |
| spec:metres | Collecte spécialisée | ok |  |
| spec:cctp | Collecte spécialisée | ok |  |
| spec:architecture | Collecte spécialisée | ok |  |
| spec:enveloppe | Collecte spécialisée | ok |  |
| outil:registre | Consolidation | ok |  |
| fusion | Consolidation | ok |  |
| outil:registre | Consolidation | ok |  |
| spec:synthese_interlots | Échanges inter-lots | ok |  |
| outil:routage-r1 | Échanges inter-lots | ok |  |
| echange:r1:cctp | Échanges inter-lots | ok |  |
| echange:r1:architecture | Échanges inter-lots | ok |  |
| echange:r1:economie | Échanges inter-lots | ok |  |
| echange:r1:enveloppe | Échanges inter-lots | ok |  |
| echange:r1:synthese_interlots | Échanges inter-lots | ok |  |
| echange:r1:metres | Échanges inter-lots | ok |  |
| outil:registre | Échanges inter-lots | ok |  |
| outil:selection | Vérification contradictoire | ok |  |
| verif:ENV-003:interpretation | Vérification contradictoire | ok |  |
| verif:ARC-003:calcul | Vérification contradictoire | ok |  |
| verif:ARC-001:interpretation | Vérification contradictoire | ok |  |
| verif:SYN-001:calcul | Vérification contradictoire | ok |  |
| verif:ARC-002:calcul | Vérification contradictoire | ok |  |
| verif:ARC-004:calcul | Vérification contradictoire | ok |  |
| verif:ARC-005:interpretation | Vérification contradictoire | ok |  |
| verif:CCT-001:interpretation | Vérification contradictoire | ok |  |
| verif:ECO-002:calcul | Vérification contradictoire | ok |  |
| verif:ECO-005:interpretation | Vérification contradictoire | ok |  |
| redaction | Livrables | ok |  |

## Plan d'analyse retenu

```json
{
  "actifs": [
    {
      "cle": "economie",
      "raison": "3 pièce(s) quantitative(s)"
    },
    {
      "cle": "metres",
      "raison": "pièces quantitatives et sources dimensionnelles présentes"
    },
    {
      "cle": "cctp",
      "raison": "4 pièce(s) écrite(s) contractuelle(s)"
    },
    {
      "cle": "architecture",
      "raison": "4 pièce(s) de la discipline architecture"
    },
    {
      "cle": "enveloppe",
      "raison": "3 pièce(s) de la discipline enveloppe"
    }
  ],
  "inactifs": [
    {
      "cle": "interieur",
      "raison": "aucune pièce de cette discipline"
    },
    {
      "cle": "electricite",
      "raison": "aucune pièce de cette discipline"
    },
    {
      "cle": "structure_go",
      "raison": "plafond du mode rapide (2 agents techniques)"
    },
    {
      "cle": "bim",
      "raison": "plafond du mode rapide (2 agents techniques)"
    },
    {
      "cle": "cvc_plomberie",
      "raison": "plafond du mode rapide (2 agents techniques)"
    },
    {
      "cle": "references",
      "raison": "non prévu en mode rapide"
    },
    {
      "cle": "opc",
      "raison": "non prévu en mode rapide et aucune pièce de planning"
    }
  ]
}
```

## Limites et réductions de périmètre

- agent structure_go non lancé (plafond du mode rapide) alors que 3 pièce(s) de la discipline structure_go
- agent bim non lancé (plafond du mode rapide) alors que 1 maquette(s) IFC
- agent cvc_plomberie non lancé (plafond du mode rapide) alors que 1 pièce(s) de la discipline cvc_plomberie
- 6 constat(s) non vérifié(s) faute de place dans le plafond du mode rapide : MET-004, MET-005, SYN-002, SYN-003, SYN-004, ENV-004
- critique de complétude par agent non lancée en mode rapide : seule la couverture déterministe (documents jamais examinés, lots sans analyse) figure dans les limites

<!-- controle_qualite -->

## Contrôle qualité automatique des livrables

**Verdict** : conforme_avec_reserves

- Q01 présence des livrables : ok
- Q02 registre CSV cohérent : ok
- Q03 intégrité des sources : ok
- Q04 aucun constat non corroboré présenté comme établi : ok
- Q05 synthèse cohérente avec les statuts : ok
- Q06 calculs des constats corroborés vérifiés : ok
- Q07 écarts du rapprochement recalculés : ok
- Q08 impacts chiffrés justifiés : ok
- Q09 références normatives traçables : ok
- Q10 limites complètes : ok
- Q11 pas de doublon résiduel évident : ok
- Q12 citations retrouvées : ok

**Avertissements**

- Q05 synthèse : CCT-005 cité avec le statut « a_verifier » (étiqueté dans le rapport)
- Q05 synthèse : MET-007 cité avec le statut « a_verifier » (étiqueté dans le rapport)
- Q05 synthèse : SYN-003 cité avec le statut « a_verifier » (étiqueté dans le rapport)
- Q05 synthèse : ARC-006 cité avec le statut « a_verifier » (étiqueté dans le rapport)
- Q05 synthèse : CCT-008 cité avec le statut « a_verifier » (étiqueté dans le rapport)
- Q05 synthèse : ENV-004 cité avec le statut « a_verifier » (étiqueté dans le rapport)
- Q05 synthèse : CCT-005 cité avec le statut « a_verifier » (étiqueté dans le rapport)
- Q05 synthèse : SYN-003 cité avec le statut « a_verifier » (étiqueté dans le rapport)
- Q05 synthèse : ENV-004 cité avec le statut « a_verifier » (étiqueté dans le rapport)
