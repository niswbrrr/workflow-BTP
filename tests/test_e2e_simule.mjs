#!/usr/bin/env node
// Test de bout en bout SIMULÉ : le vrai script du workflow, les vrais outils Python,
// des agents scriptés (tests/scenario/scenario.mjs) à la place du modèle.
// Usage : node tests/test_e2e_simule.mjs [--bavard] [--garder]
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { executerWorkflow } from './lib/runtime.mjs'
import { creerAgents } from './lib/agents_simules.mjs'
import * as scenario from './scenario/scenario.mjs'

const racine = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const WF = path.join(racine, '.claude/workflows/audit-dossier-btp.js')
const OUTILS = path.join(racine, 'audit-dossier-btp/tools')
const DOSSIER = path.join(racine, 'tests/dossier_test')
const bavard = process.argv.includes('--bavard')
const garder = process.argv.includes('--garder')
const base = fs.mkdtempSync(path.join(os.tmpdir(), 'audit-btp-e2e-'))
const echecs = []
const verifier = (cond, msg) => { if (!cond) echecs.push(msg); console.log(`  ${cond ? '✔' : '✘'} ${msg}`) }

async function cas(nom, args, options = {}) {
  console.log(`\n=== ${nom} ===`)
  const { resultat, trace } = await executerWorkflow(WF, { args, agents: creerAgents(scenario, options), bavard, budgetTotal: options.budgetTotal ?? null })
  for (const e of trace.erreurs) console.log('  ! ' + e)
  return { resultat, trace }
}

// ---------------------------------------------------------------- scénario A
{
  const sortie = path.join(base, 'A', 'livrables_audit')
  const { resultat, trace } = await cas('A — mode standard, fichier invalide injecté, synthèse fautive', `${DOSSIER} mode=standard sortie=${sortie} outils=${OUTILS}`,
    { pannes: ['fichier_invalide:cctp'], redactionFautive: true })
  verifier(trace.erreurs.length === 0, 'aucune erreur de runtime (schémas, phases, exceptions)')
  verifier(resultat && resultat.statut && resultat.statut.startsWith('termine'), `statut final « ${resultat && resultat.statut} »`)
  const labels = trace.appels.map((a) => a.label)
  verifier(labels.includes('reparation:cctp'), 'le fichier de constats invalide est détecté et réparé')
  verifier(labels.includes('redaction#correction'), 'la synthèse fautive déclenche une correction bornée')
  verifier(labels.filter((l) => l.startsWith('echange:r1:')).length >= 4, 'au moins 4 destinataires répondent au tour 1')
  verifier(labels.some((l) => l.startsWith('arbitre:ARC-001')), "le désaccord sur la dalle est arbitré")
  verifier(labels.includes('fusion') && labels.includes('fusion#2'), 'deux passages du juge de dédoublonnage')
  verifier(trace.appels.filter((a) => a.label.startsWith('outil:')).every((a) => a.effort === 'low'), "les opérateurs d'outils tournent en effort low")
  verifier(trace.appels.filter((a) => a.label === 'outil:controles-amont').length === 1, 'contrôles amont en un seul passage')
  verifier((resultat.limites || []).some((l) => l.includes('D007/D009') && l.includes('non tabulaire')), 'rapprochement avec un plan écarté et déclaré')
  const dpgf7 = JSON.parse(fs.readFileSync(path.join(sortie, '_travail/controles/dpgf_D007.json'), 'utf8'))
  verifier(dpgf7.feuilles.length === 2 && dpgf7.feuilles.some((f) => f.nom === 'Recapitulatif' && !f.erreur), 'métré déclaré deux fois : un seul contrôle, toutes feuilles, pas d\'écrasement')
  const actifs = (resultat && resultat.agents_actifs) || []
  for (const k of ['economie', 'metres', 'cctp', 'architecture', 'enveloppe', 'structure_go', 'cvc_plomberie', 'bim', 'references', 'synthese_interlots', 'opc']) verifier(actifs.includes(k), `agent ${k} activé`)
  verifier(!actifs.includes('electricite') && !actifs.includes('interieur'), 'électricité et intérieur non lancés (aucune pièce)')
  try {
    const out = execFileSync('python3', [path.join(racine, 'tests/verifier_e2e.py'), sortie], { encoding: 'utf8' })
    process.stdout.write(out)
  } catch (e) {
    process.stdout.write(e.stdout || '')
    echecs.push('vérifications Python du scénario A en échec')
  }
}

// ---------------------------------------------------------------- scénario B
{
  const sortie = path.join(base, 'B', 'livrables_audit')
  const { resultat, trace } = await cas('B — mode rapide, agent architecture en panne (2 fois)', { dossier: DOSSIER, mode: 'rapide', sortie, outils: OUTILS },
    { pannes: ['spec:architecture', 'spec:architecture#2'] })
  verifier(trace.erreurs.length === 0, 'aucune erreur de runtime')
  verifier(resultat && resultat.statut && resultat.statut.startsWith('termine'), `le workflow se termine malgré la panne (« ${resultat && resultat.statut} »)`)
  verifier(trace.appels.some((a) => a.label === 'spec:architecture#2'), 'une seule relance de l\'agent en panne')
  verifier((resultat.limites || []).some((l) => l.includes('architecture') && l.includes('aucun résultat')), 'la panne figure dans les limites')
  verifier((resultat.agents_non_lances || []).some((x) => x.cle === 'structure_go' && x.raison.includes('plafond')), 'plafond du mode rapide signalé (structure_go non lancé)')
  verifier(!trace.appels.some((a) => a.label.startsWith('completude')), 'pas de critique de complétude en mode rapide')
  const rapport = fs.readFileSync(path.join(sortie, 'rapport_audit_dossier_btp.md'), 'utf8')
  verifier(rapport.includes('spec:architecture'), 'le rapport mentionne l\'agent en échec dans ses limites')
}

// ---------------------------------------------------------------- scénarios C, D, E
{
  const { resultat } = await cas('C — arguments manquants', '', {})
  verifier(resultat && resultat.statut === 'arguments_manquants', 'arrêt immédiat avec message d\'aide')
}
{
  const { resultat, trace } = await cas('D — dossier introuvable', { dossier: path.join(base, 'nexiste_pas'), outils: OUTILS, sortie: path.join(base, 'D') }, {})
  verifier(resultat && resultat.statut === 'interrompu', 'interruption propre')
  verifier(trace.appels.length === 1, 'aucun agent lancé après l\'échec de l\'environnement')
}
{
  const sortie = path.join(base, 'E', 'livrables_audit')
  const { resultat, trace } = await cas('E — budget serré (24 agents simulés)', { dossier: DOSSIER, mode: 'standard', sortie, outils: OUTILS }, { budgetTotal: 480000 })
  verifier(resultat !== null, 'le script ne plante pas quand le budget s\'épuise')
  verifier(resultat && String(resultat.statut).startsWith('termine'), `les livrables sont tout de même produits grâce à la réserve (« ${resultat && resultat.statut} »)`)
  verifier(fs.existsSync(path.join(sortie, 'rapport_audit_dossier_btp.md')), 'rapport présent')
  verifier((resultat.limites || []).some((l) => l.includes('budget')), 'la réduction de périmètre est déclarée dans les limites')
  verifier(trace.erreurs.filter((e) => !e.includes('budget')).length === 0, 'aucune autre erreur')
  console.log(`  (statut : ${resultat.statut} ; agents : ${trace.appels.length})`)
}

console.log(`\nRépertoire de test : ${base}${garder ? '' : ' (supprimé)'}`)
if (!garder) fs.rmSync(base, { recursive: true, force: true })
if (echecs.length) { console.log(`\n${echecs.length} vérification(s) en échec :\n- ` + echecs.join('\n- ')); process.exit(1) }
console.log('\nTous les scénarios simulés sont conformes.')
