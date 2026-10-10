// Reproduction locale des règles du moteur de workflows de Claude Code 2.1.x
// (relevées dans le binaire : fonction de lecture de `meta`, compilation du corps).
// Sert au validateur et au runtime simulé. Ne remplace pas le moteur réel.
import { createRequire } from 'node:module'
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'

const ici = path.dirname(fileURLToPath(import.meta.url))

export function charger(nom) {
  const bases = [path.join(ici, '..'), process.cwd(), ...(process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean), '/opt/node-tools/node_modules']
  for (const b of bases) {
    try {
      return createRequire(path.join(b, 'x.js'))(nom)
    } catch (_) { /* base suivante */ }
  }
  throw new Error(`module « ${nom} » introuvable : npm install --prefix tests (voir tests/package.json)`)
}

export const TAILLE_MAX = 524288 // octets (constante Sv du moteur)

// caractères de contrôle ou invisibles refusés (le moteur refuse ce qu'un dialogue d'approbation ne peut pas montrer)
const plages = [[0x00, 0x08], [0x0b, 0x0c], [0x0e, 0x1f], [0x7f, 0x7f], [0x200b, 0x200f], [0x2028, 0x2029], [0x202a, 0x202e], [0x2066, 0x2069], [0xfeff, 0xfeff]]
const INTERDITS = new RegExp('[' + plages.map(([a, b]) => '\\u' + a.toString(16).padStart(4, '0') + '-\\u' + b.toString(16).padStart(4, '0')).join('') + ']')

export function caracteresInterdits(texte) {
  const lignes = texte.split('\n')
  const out = []
  lignes.forEach((l, i) => {
    const sansCR = l.endsWith('\r') ? l.slice(0, -1) : l
    if (sansCR.includes('\r') || INTERDITS.test(sansCR)) out.push(i + 1)
  })
  return out
}

function valeurLitterale(n) {
  switch (n.type) {
    case 'Literal': return n.value
    case 'ArrayExpression': return n.elements.map((e) => {
      if (e === null) throw new Error('sparse arrays not allowed')
      if (e.type === 'SpreadElement') throw new Error('spread not allowed in meta')
      return valeurLitterale(e)
    })
    case 'ObjectExpression': return objetLitteral(n)
    case 'TemplateLiteral':
      if (n.expressions.length) throw new Error('template interpolation not allowed in meta')
      return n.quasis.map((q) => q.value.cooked ?? '').join('')
    case 'UnaryExpression':
      if (n.operator === '-' && n.argument.type === 'Literal' && typeof n.argument.value === 'number') return -n.argument.value
      throw new Error('only negative-number unary allowed in meta')
    default: throw new Error(`non-literal node type in meta: ${n.type}`)
  }
}

function objetLitteral(n) {
  const o = Object.create(null)
  for (const p of n.properties) {
    if (p.type !== 'Property') throw new Error('only plain properties allowed in meta')
    if (p.computed) throw new Error('computed keys not allowed in meta')
    if (p.method || p.kind !== 'init') throw new Error('methods/accessors not allowed in meta')
    const k = p.key.type === 'Identifier' ? p.key.name : String(p.key.value)
    if (['__proto__', 'constructor', 'prototype'].includes(k)) throw new Error(`reserved key name not allowed in meta: ${k}`)
    o[k] = valeurLitterale(p.value)
  }
  return o
}

function controlerMeta(m) {
  if (typeof m.name !== 'string' || !m.name) return { error: 'meta.name must be a non-empty string' }
  if (typeof m.description !== 'string' || !m.description) return { error: 'meta.description must be a non-empty string' }
  const phases = Array.isArray(m.phases) ? m.phases.filter((p) => p && typeof p === 'object' && typeof p.title === 'string') : undefined
  return { meta: { name: m.name, description: m.description, whenToUse: typeof m.whenToUse === 'string' ? m.whenToUse : undefined, phases } }
}

function marcher(noeud, visite, parents = []) {
  if (!noeud || typeof noeud.type !== 'string') return
  visite(noeud, parents)
  for (const [k, v] of Object.entries(noeud)) {
    if (k === 'loc' || k === 'start' || k === 'end') continue
    if (Array.isArray(v)) v.forEach((x) => x && typeof x.type === 'string' && marcher(x, visite, parents.concat(noeud)))
    else if (v && typeof v.type === 'string') marcher(v, visite, parents.concat(noeud))
  }
}

// Analyse un script de workflow comme le moteur : renvoie { meta, corps } ou { error }
export function analyserScript(texte) {
  const acorn = charger('acorn')
  if (Buffer.byteLength(texte, 'utf8') > TAILLE_MAX) return { error: `Script exceeds ${TAILLE_MAX} bytes` }
  const lignes = caracteresInterdits(texte)
  if (lignes.length) return { error: `script contains control characters (lignes ${lignes.join(', ')})` }
  let ast
  try {
    ast = acorn.parse(texte, { ecmaVersion: 'latest', sourceType: 'module', allowAwaitOutsideFunction: true, allowReturnOutsideFunction: true, locations: true })
  } catch (e) {
    return { error: `Script parse error: ${e.message}. Workflow scripts must be plain JavaScript.` }
  }
  const premier = ast.body[0]
  const decl = premier && premier.type === 'ExportNamedDeclaration' ? premier.declaration : null
  if (!decl || decl.type !== 'VariableDeclaration' || decl.kind !== 'const' || decl.declarations.length !== 1 ||
      decl.declarations[0].id.name !== 'meta' || decl.declarations[0].init?.type !== 'ObjectExpression') {
    return { error: '`export const meta = { name, description, phases }` must be the FIRST statement in the script' }
  }
  let brut
  try { brut = objetLitteral(decl.declarations[0].init) } catch (e) { return { error: `meta must be a pure literal: ${e.message}` } }
  const m = controlerMeta(brut)
  if (m.error) return m
  const corps = texte.slice(premier.end).replace(/^[;\s]*\n/, '').trimStart()
  return { meta: m.meta, corps, brut }
}

// Compilation du corps comme le moteur : enveloppe async stricte + interdits
export function compilerCorps(corps) {
  const acorn = charger('acorn')
  const enveloppe = `(async () => {'use strict';\n${corps}\n})()`
  const erreurs = []
  let ast
  try {
    ast = acorn.parse(enveloppe, { ecmaVersion: 'latest', sourceType: 'script', allowHashBang: true, locations: true })
  } catch (e) {
    return { erreurs: [`parse : ${e.message}`] }
  }
  marcher(ast, (n) => {
    if (n.type === 'WithStatement') erreurs.push("'with' statements are not supported in workflow scripts.")
    if (n.type === 'ImportExpression') erreurs.push('import() is not available in workflow scripts.')
    if (n.type === 'VariableDeclaration' && n.kind === 'await using') erreurs.push("'await using' declarations are not supported in workflow scripts.")
    if (n.type === 'MemberExpression' && n.object.type === 'Identifier' && n.property.type === 'Identifier') {
      if (n.object.name === 'Date' && n.property.name === 'now') erreurs.push(`Date.now() interdit (ligne ${n.loc.start.line - 1})`)
      if (n.object.name === 'Math' && n.property.name === 'random') erreurs.push(`Math.random() interdit (ligne ${n.loc.start.line - 1})`)
    }
    if (n.type === 'NewExpression' && n.callee.type === 'Identifier' && n.callee.name === 'Date' && n.arguments.length === 0) erreurs.push(`new Date() sans argument interdit (ligne ${n.loc.start.line - 1})`)
  })
  try {
    // contrôle supplémentaire par le compilateur V8, comme le moteur ($ie)
    // eslint-disable-next-line no-new-func
    Function(`async function _check() {'use strict';\n${corps}\n}`)
  } catch (e) {
    erreurs.push('V8 : ' + e.message)
  }
  return { erreurs, ast }
}

// Contrôle de bonne forme d'un schéma passé à agent() : racine objet avec properties, required ⊆ properties
export function controlerSchema(s, chemin = '$') {
  const err = []
  if (!s || typeof s !== 'object') return [`${chemin} : schéma absent`]
  if (chemin === '$' && (s.type !== 'object' || !s.properties)) err.push(`${chemin} : la racine doit être {type:'object', properties:{…}}`)
  if (s.required && s.properties) for (const r of s.required) if (!(r in s.properties)) err.push(`${chemin} : required « ${r} » absent de properties`)
  if (s.properties) for (const [k, v] of Object.entries(s.properties)) err.push(...controlerSchema(v, `${chemin}.${k}`).filter((x) => !x.endsWith('schéma absent')))
  if (s.items) err.push(...controlerSchema(s.items, `${chemin}[]`).filter((x) => !x.endsWith('schéma absent')))
  return err
}

export function lireFichier(p) { return fs.readFileSync(p, 'utf8') }
