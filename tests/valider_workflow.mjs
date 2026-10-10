#!/usr/bin/env node
// Validateur statique d'un script de workflow, fidèle aux règles du moteur Claude Code.
// Usage : node tests/valider_workflow.mjs [.claude/workflows/audit-dossier-btp.js]
import path from 'node:path'
import { analyserScript, compilerCorps, lireFichier } from './lib/moteur.mjs'

const fichier = process.argv[2] || path.join(process.cwd(), '.claude/workflows/audit-dossier-btp.js')
const texte = lireFichier(fichier)
const rapport = { fichier, octets: Buffer.byteLength(texte, 'utf8'), erreurs: [], avertissements: [] }

const a = analyserScript(texte)
if (a.error) {
  rapport.erreurs.push(a.error)
} else {
  rapport.meta = { name: a.meta.name, description: a.meta.description.slice(0, 80) + '…', phases: (a.meta.phases || []).map((p) => p.title) }
  if (!/^[a-z0-9-]+$/.test(a.meta.name)) rapport.avertissements.push('meta.name devrait être en minuscules avec tirets (nom de la commande slash)')
  const c = compilerCorps(a.corps)
  rapport.erreurs.push(...c.erreurs)
  // titres de phase : chaque titre déclaré doit apparaître littéralement dans le corps, et inversement
  const litteraux = new Set()
  const re = /'([^'\\\n]{3,80})'/g
  let m
  while ((m = re.exec(a.corps))) litteraux.add(m[1])
  for (const p of (a.meta.phases || [])) if (!litteraux.has(p.title)) rapport.erreurs.push(`titre de phase « ${p.title} » déclaré dans meta mais jamais utilisé dans le corps`)
  if (!/\bphase\(/.test(a.corps)) rapport.avertissements.push('aucun appel phase()')
  if (!/schema:/.test(a.corps)) rapport.avertissements.push('aucun schéma structuré passé à agent()')
}
rapport.statut = rapport.erreurs.length ? 'invalide' : 'ok'
console.log(JSON.stringify(rapport, null, 2))
process.exit(rapport.erreurs.length ? 1 : 0)
