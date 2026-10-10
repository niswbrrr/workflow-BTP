// Agents simulés : jouent un scénario scripté SANS modèle.
// - les opérateurs d'outils exécutent réellement les commandes que le workflow leur donne ;
// - les agents « métier » écrivent les fichiers prévus par le scénario aux chemins indiqués
//   dans leur prompt, puis exécutent la commande de validation trouvée dans ce prompt.
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

function bash(commande) {
  try {
    const out = execFileSync('bash', ['-c', commande], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 })
    return { code: 0, stdout: out, stderr: '' }
  } catch (e) {
    return { code: e.status || 1, stdout: e.stdout || '', stderr: String(e.stderr || e.message).slice(0, 500) }
  }
}
function dernierJson(stdout) {
  const lignes = stdout.trim().split('\n').reverse()
  for (const l of lignes) { try { const v = JSON.parse(l); if (v && typeof v === 'object') return v } catch (_) { /* ligne suivante */ } }
  return null
}
const ecrire = (p, obj) => { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, JSON.stringify(obj, null, 2), 'utf8') }
const lire = (p) => JSON.parse(fs.readFileSync(p, 'utf8'))

// commande de validation présente dans le prompt (forme produite par validerCmd du workflow)
const RE_VALID = /(\S+ "[^"]*registre\.py" validate --fichier "([^"]*)" --type (\w+) --travail "([^"]*)"(?: --agent [\w]+)?(?: --actifs [\w,]+)?)/
function validation(prompt) {
  const m = prompt.match(RE_VALID)
  if (!m) throw new Error('commande de validation introuvable dans le prompt')
  return { commande: m[1], fichier: m[2], type: m[3], travail: m[4] }
}
function valider(commande) {
  const r = bash(commande)
  const j = dernierJson(r.stdout)
  return j && j.statut === 'ok' ? 'ok' : 'invalide'
}
function indexDepuisFichier(p, v) {
  const d = lire(p)
  return {
    agent: d.agent, statut_analyse: d.statut_analyse, motif_statut: d.motif_statut || '', fichier: p, validation: v,
    constats: d.constats.map((c) => ({ finding_id: c.finding_id, title: c.title, lot: c.lot, finding_type: c.finding_type, severity: c.severity, priority: c.priority })),
    transmissions: d.transmissions.map((t) => ({ destinataire: t.destinataire, constat_id: t.constat_id || '', question: t.question })),
    documents_examines: d.documents_examines.map((x) => x.doc_id), limites: d.limites || [],
  }
}

export function creerAgents(scenario, options = {}) {
  const pannes = new Set(options.pannes || [])
  const journal = options.journal || []
  const etat = { redactions: 0 }

  const operateur = ({ prompt }) => {
    const ecr = prompt.match(/écris EXACTEMENT le contenu JSON suivant[^\n]*dans le fichier (.+?) avec l'outil Write :\n(.+?)(?:\n\nÉtapes :|$)/s)
    if (ecr) { fs.mkdirSync(path.dirname(ecr[1]), { recursive: true }); fs.writeFileSync(ecr[1], ecr[2].trim(), 'utf8') }
    const resultats = []
    const re = /^\d+\. \[etape: ([^\]]+)\]\n(.+)$/gm
    let m
    while ((m = re.exec(prompt))) {
      const r = bash(m[2])
      const j = dernierJson(r.stdout)
      resultats.push({ etape: m[1], code_retour: j ? r.code : (r.code || 1), sortie_json: j || {}, ...(j ? {} : { erreur: r.stderr || 'sortie non JSON' }) })
    }
    const ko = resultats.filter((x) => x.code_retour !== 0).length
    return { statut: ko === 0 ? 'ok' : (ko === resultats.length ? 'echec' : 'partiel'), resultats, erreurs: [] }
  }

  const environnement = ({ prompt }) => {
    const config = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude')
    const cands = prompt.match(/parmi : (.+?)\. Donne/)[1].split(' ; ').map((c) => c.replace(/^~/, os.homedir()).replace('${CLAUDE_CONFIG_DIR:-$HOME/.claude}', config))
    const outils = cands.map((c) => path.resolve(c)).find((c) => fs.existsSync(path.join(c, 'preflight.py')))
    if (!outils) return { statut: 'echec', python: 'python3', outils: '', preflight: {}, inventaire: {}, erreurs: ['outils introuvables'] }
    const ligne = prompt.match(/Exécute : <python> "<outils>\/preflight\.py" (.+)/)[1]
    const pre = dernierJson(bash(`python3 "${outils}/preflight.py" ${ligne}`).stdout) || {}
    let inv = {}
    if (pre.statut === 'ok') inv = dernierJson(bash(`python3 "${outils}/inventaire.py" --source "${pre.source.chemin}" --travail "${pre.travail}"`).stdout) || {}
    return { statut: pre.statut === 'ok' ? 'ok' : 'echec', python: 'python3', outils, preflight: pre, inventaire: inv, erreurs: pre.statut === 'ok' ? [] : [pre.erreur || 'preflight en échec'] }
  }

  const documentaliste = ({ prompt }) => {
    const v = validation(prompt)
    ecrire(v.fichier, scenario.classement)
    const ok = valider(v.commande)
    const c = scenario.classement
    return {
      fichier: v.fichier, validation: ok, dossier_exploitable: c.dossier_exploitable, motif: '',
      documents: c.documents.map((d) => ({ doc_id: d.doc_id, type_piece: d.type_piece, disciplines: d.disciplines, lots: d.lots, statut_exploitation: d.statut_exploitation, indice: d.indice || '' })),
      pieces_quantitatives: c.pieces_quantitatives, rapprochements_proposes: c.rapprochements_proposes,
      sujets_hors_chartes: c.sujets_hors_chartes, questions_cadrage: c.questions_cadrage,
      versions_concurrentes: c.versions_concurrentes, documents_manquants: c.documents_manquants,
    }
  }

  const specialiste = (cle) => ({ prompt, label }) => {
    const v = validation(prompt)
    let contenu = scenario.constats[cle]
    if (!contenu) {
      contenu = { agent: cle, phase: 'collecte', statut_analyse: 'terminee', motif_statut: null, documents_examines: [], constats: [], transmissions: [], ras: [{ sujet: 'agent simulé', commentaire: 'aucun constat prévu par le scénario' }], limites: [] }
    }
    if (pannes.has('fichier_invalide:' + cle) && !label.includes('#2') && !label.startsWith('reparation')) {
      ecrire(v.fichier, contenu)
      const index = indexDepuisFichier(v.fichier, 'ok') // l'agent annonce « ok » à tort…
      const casse = JSON.parse(JSON.stringify(contenu))
      delete casse.constats[0].severity
      ecrire(v.fichier, casse) // … mais son fichier est invalide : la consolidation doit le détecter
      return index
    }
    ecrire(v.fichier, contenu)
    return indexDepuisFichier(v.fichier, valider(v.commande))
  }

  const echange = (dest) => ({ prompt }) => {
    const v = validation(prompt)
    const tour = Number(prompt.match(/Tour d'échanges n° (\d+)/)[1])
    const aTraiter = lire(path.join(v.travail, 'echanges', `r${tour}`, 'a_traiter.json'))
    const reps = []
    for (const t of aTraiter.par_destinataire[dest] || []) {
      const s = (scenario.reponses[dest] || {})[t.constat_id] || { verdict: 'non_resolu', justification: 'simulation : aucun élément nouveau dans les pièces' }
      reps.push({ transmission_id: t.transmission_id, constat_id: t.constat_id, verdict: s.verdict, justification: s.justification, elements_nouveaux: s.elements_nouveaux || [], sources: s.sources || [] })
    }
    ecrire(v.fichier, { agent: dest, round: tour, reponses: reps, constats: [], corrections: [], retraits: [], transmissions: [], limites: [] })
    return { agent: dest, fichier: v.fichier, validation: valider(v.commande), reponses: reps.map((r) => ({ transmission_id: r.transmission_id, verdict: r.verdict })), nouveaux_constats: [], corrections: [], retraits: [], nouvelles_transmissions: 0 }
  }

  const verificateur = (fid, lentille) => ({ prompt }) => {
    const v = validation(prompt)
    const s = ((scenario.verifications[fid] || {})[lentille]) || { verdict: 'confirme', justification: 'simulation : preuve recontrôlée dans les pièces, citation retrouvée, pas de réfutation plausible' }
    ecrire(v.fichier, { constat_id: fid, lentille, verdict: s.verdict, justification: s.justification, elements_nouveaux: [], sources: [], correction_proposee: null, confiance: 'moyenne' })
    return { constat_id: fid, lentille, verdict: s.verdict, fichier: v.fichier, validation: valider(v.commande), resume: s.justification.slice(0, 120) }
  }

  const arbitre = (fid) => ({ prompt }) => {
    const v = validation(prompt)
    const s = scenario.arbitrages[fid] || { decision: 'desaccord_persistant', motif: 'simulation : aucun élément décisif dans les pièces', elements_decisifs: [], positions: [{ acteur: 'simulation', position: 'indéterminée', argument: null }], questions_pour_moe: [] }
    ecrire(v.fichier, { constat_id: fid, sources: [], nouveau_type: null, ...s })
    return { constat_id: fid, decision: s.decision, fichier: v.fichier, validation: valider(v.commande), resume: s.motif.slice(0, 120) }
  }

  const fusion = ({ prompt }) => {
    const v = validation(prompt)
    const reg = lire(path.join(v.travail, 'registre.json'))
    const existant = fs.existsSync(v.fichier) ? lire(v.fichier).decisions : []
    const deja = new Set(existant.map((d) => [...d.ids].sort().join('|')))
    const decisions = [...existant]
    let nf = 0
    let nd = 0
    for (const c of reg.doublons_candidats) {
      const cle = [...c.ids].sort().join('|')
      if (deja.has(cle)) continue
      deja.add(cle)
      const s = scenario.fusions.find((x) => [...x.ids].sort().join('|') === cle)
      if (s) { decisions.push(s); nf += s.decision === 'fusionner' ? 1 : 0; nd += s.decision === 'distincts' ? 1 : 0 } else { decisions.push({ ids: c.ids, decision: 'distincts', motif: 'simulation : preuves ou actions différentes', id_retenu: null }); nd++ }
    }
    ecrire(v.fichier, { decisions })
    journal.push({ fusion: decisions.length })
    return { fichier: v.fichier, validation: valider(v.commande), fusions: nf, distincts: nd }
  }

  const completude = (passe) => ({ prompt }) => {
    const v = validation(prompt)
    const contenu = scenario.completude[passe] || { agent: 'completude', phase: 'completude', statut_analyse: 'terminee', motif_statut: null, documents_examines: [], constats: [], transmissions: [], ras: [{ sujet: 'couverture', commentaire: 'simulation : aucune lacune nouvelle' }], limites: [] }
    ecrire(v.fichier, contenu)
    return indexDepuisFichier(v.fichier, valider(v.commande))
  }

  const redaction = ({ prompt, label }) => {
    const v = validation(prompt)
    etat.redactions++
    const reg = lire(path.join(v.travail, 'registre.json'))
    const etablis = reg.constats.filter((c) => c.status === 'corrobore')
    const ouverts = reg.constats.filter((c) => ['conteste', 'non_resolu'].includes(c.status))
    const refute = reg.constats.find((c) => c.status === 'refute')
    const messages = etablis.slice(0, 4).map((c) => ({ texte: c.title, constats: [c.finding_id] }))
    if (ouverts.length) messages.push({ texte: 'Points en désaccord, à confirmer par la maîtrise d\'œuvre', constats: ouverts.map((c) => c.finding_id) })
    if (options.redactionFautive && etat.redactions === 1 && refute) messages.push({ texte: 'Erreur volontaire du scénario : constat réfuté cité', constats: [refute.finding_id] })
    const decisions = etablis.filter((c) => c.priority === 'P1').slice(0, 4).map((c) => ({ decision: c.recommended_action, constats: [c.finding_id], acteur: c.responsible_party, echeance: c.decision_deadline }))
    ecrire(v.fichier, { appreciation_globale: 'Synthèse simulée : le dossier présente des incohérences de quantités et une interface de réservations non attribuée.', messages_cles: messages, decisions_prioritaires: decisions, avertissements: [] })
    return { fichier: v.fichier, validation: valider(v.commande), messages: messages.length, decisions: decisions.length }
  }

  const revue = ({ prompt }) => {
    const v = validation(prompt)
    ecrire(v.fichier, { verdict: 'conforme', problemes: [] })
    return { fichier: v.fichier, verdict: 'conforme', problemes_bloquants: 0, resume: 'simulation : rien de bloquant', non_valide: ['lisibilité réelle non évaluée par la simulation'] }
  }

  return (label) => {
    if (pannes.has(label)) return () => null
    if (label === 'outil:environnement') return environnement
    if (label.startsWith('outil:')) return operateur
    if (label.startsWith('documentaliste')) return documentaliste
    if (label === 'fusion' || label === 'fusion#2') return fusion
    if (label.startsWith('redaction')) return redaction
    if (label === 'revue-qualite') return revue
    let m
    if ((m = label.match(/^(?:spec|reparation):([a-z_0-9]+)(?:#\d)?$/))) return specialiste(m[1])
    if ((m = label.match(/^echange:r\d+:([a-z_0-9]+)$/))) return echange(m[1])
    if ((m = label.match(/^verif:([^:]+):(\w+)$/))) return verificateur(m[1], m[2])
    if ((m = label.match(/^arbitre:(.+)$/))) return arbitre(m[1])
    if ((m = label.match(/^completude:p(\d+)$/))) return completude(Number(m[1]))
    return null
  }
}
