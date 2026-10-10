// Runtime simulé : exécute un script de workflow avec les primitives du moteur
// (agent, parallel, pipeline, phase, log, args, budget) et des agents scriptés.
import vm from 'node:vm'
import { analyserScript, charger, compilerCorps, controlerSchema, lireFichier } from './moteur.mjs'

export async function executerWorkflow(fichier, { args, agents, concurrence = 4, budgetTotal = null, coutParAgent = 20000, bavard = false }) {
  const texte = lireFichier(fichier)
  const a = analyserScript(texte)
  if (a.error) throw new Error('script invalide : ' + a.error)
  const c = compilerCorps(a.corps)
  if (c.erreurs.length) throw new Error('corps invalide : ' + c.erreurs.join(' ; '))
  const Ajv = charger('ajv')
  const ajv = new Ajv({ allErrors: true })

  const trace = { appels: [], phases: [], logs: [], erreurs: [], meta: a.meta }
  let actifs = 0
  const attente = []
  const prendre = () => new Promise((r) => { if (actifs < concurrence) { actifs++; r() } else attente.push(r) })
  const rendre = () => { const n = attente.shift(); if (n) n(); else actifs-- }
  let depense = 0
  const budget = {
    total: budgetTotal,
    spent: () => depense,
    remaining: () => (budgetTotal === null ? Infinity : Math.max(0, budgetTotal - depense)),
  }
  let phaseCourante = null
  const contexte = vm.createContext({})
  const versContexte = (v) => (v === undefined ? undefined : vm.runInContext('JSON.parse', contexte)(JSON.stringify(v)))

  async function agent(prompt, opts = {}) {
    if (typeof prompt !== 'string' || !prompt) throw new Error('agent() : prompt vide')
    if (budgetTotal !== null && depense >= budgetTotal) throw new Error('token budget exhausted')
    if (trace.appels.length >= 1000) throw new Error('Workflow agent() call cap reached')
    const rec = { label: opts.label, phase: opts.phase || phaseCourante, effort: opts.effort || null, schema: !!opts.schema, taillePrompt: prompt.length }
    if (opts.schema) {
      const e = controlerSchema(opts.schema)
      if (e.length) { rec.erreursSchema = e; trace.erreurs.push(`${opts.label} : schéma mal formé : ${e.join(' ; ')}`) }
    }
    trace.appels.push(rec)
    await prendre()
    try {
      depense += coutParAgent
      const h = agents(opts.label || '')
      if (!h) { rec.resultat = 'sans_simulation'; trace.erreurs.push(`aucun agent simulé pour « ${opts.label} »`); return null }
      let res
      try {
        res = await h({ prompt, opts, label: opts.label })
      } catch (e) {
        rec.resultat = 'exception'
        rec.erreur = String(e && e.stack || e).slice(0, 800)
        trace.erreurs.push(`${opts.label} : exception de l'agent simulé : ${rec.erreur}`)
        return null
      }
      if (res === null || res === undefined) { rec.resultat = 'null'; return null }
      if (opts.schema) {
        const ok = ajv.validate(opts.schema, res)
        if (!ok) {
          rec.resultat = 'hors_schema'
          trace.erreurs.push(`${opts.label} : réponse hors schéma : ${ajv.errorsText(ajv.errors)}`)
          return null
        }
      }
      rec.resultat = 'ok'
      if (bavard) console.log(`    ✓ ${opts.label}`)
      return versContexte(res)
    } finally {
      rendre()
    }
  }
  const parallel = async (thunks) => {
    if (!Array.isArray(thunks)) throw new Error('parallel() attend un tableau de fonctions')
    return Promise.all(thunks.map(async (t) => { try { return await t() } catch (e) { trace.erreurs.push('parallel : ' + (e && e.message)); return null } }))
  }
  const pipeline = async (items, ...etapes) => Promise.all(items.map(async (item, i) => {
    let cur = item
    for (const et of etapes) {
      try { cur = await et(cur, item, i) } catch (e) { trace.erreurs.push('pipeline : ' + (e && e.message)); return null }
    }
    return cur
  }))
  const phase = (t) => { phaseCourante = t; trace.phases.push(t); if (bavard) console.log(`  ▶ ${t}`) }
  const log = (m) => { trace.logs.push(String(m)); if (bavard) console.log(`    » ${m}`) }

  Object.assign(contexte, { agent, parallel, pipeline, phase, log, budget, args: versContexte(args), workflow: () => { throw new Error('workflow() non simulé') } })
  vm.runInContext(`
    Math.random = () => { throw new Error('Math.random() is unavailable in workflow scripts') };
    const D = Date;
    globalThis.Date = new Proxy(D, {
      construct(t, a) { if (!a.length) throw new Error('new Date() is unavailable in workflow scripts'); return new t(...a) },
      get(t, p) { if (p === 'now') return () => { throw new Error('Date.now() is unavailable in workflow scripts') }; return t[p] },
    });`, contexte)
  const promesse = vm.runInContext(`(async () => {'use strict';\n${a.corps}\n})()`, contexte, { filename: 'workflow.js' })
  let resultat
  try {
    resultat = await promesse
  } catch (e) {
    trace.erreurs.push('le script a levé une exception : ' + (e && e.stack || e))
    resultat = null
  }
  // titres de phase utilisés à l'exécution : doivent correspondre exactement à meta.phases
  const declares = new Set((a.meta.phases || []).map((p) => p.title))
  for (const p of new Set(trace.phases.concat(trace.appels.map((x) => x.phase).filter(Boolean)))) {
    if (!declares.has(p)) trace.erreurs.push(`phase « ${p} » utilisée mais absente de meta.phases`)
  }
  trace.depense = depense
  return { resultat: resultat === null ? null : JSON.parse(JSON.stringify(resultat)), trace }
}
