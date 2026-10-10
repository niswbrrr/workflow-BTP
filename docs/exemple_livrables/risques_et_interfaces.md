# Risques de chantier, interfaces et dépendances

Les contraintes ci-dessous sont issues des pièces analysées. Les durées et délais ne sont jamais inventés : quand une échéance figure, elle provient d'une pièce ou de la nature de la décision.

| ID | Titre | Lot | Type | Gravité | Priorité | Statut | Confiance | Preuve |
|---|---|---|---|---|---|---|---|---|
| ARC-003 | Emprise 24,00 x 10,50 m (252 m2) contre salle et surface de plancher annoncées à 120 m2 | 02 Gros oeuvre / transversal | Incohérence | Critique | P1 | Corroboré | Moyenne | citation vérifiée |
| ENV-003 | Aucune pièce de couverture/étanchéité alors que la coupe montre un acrotère | Non attribué (toiture) | Omission possible | Critique | P1 | Corroboré | Faible | citation vérifiée |
| SYN-001 | Voiles BA du lot 02 (210 m2) très inférieurs aux façades à enduire du lot 03 (448,5 m2 brut) | 02 Gros oeuvre / 03 Façades | Incohérence | Critique | P1 | Corroboré | Moyenne | citation vérifiée |
| ARC-001 | Plan A-101 : 14 fenêtres à l'indice A, 12 à l'indice B (versions concurrentes) | Transversal (03 Façades, menuiseries) | Incohérence | Majeure | P1 | Corroboré | Élevée | citation vérifiée |
| ARC-002 | Dalle haute RDC : 18 cm (coupe, IFC) contre 20 cm (CCTP, DPGF) | 02 Gros oeuvre | Incohérence | Majeure | P1 | Corroboré | Élevée | citation vérifiée |
| ARC-004 | Hauteurs : 6,50 m de façade au métré, aucune hauteur totale écrite sur la coupe ; niveau R+1 à 3,20 m dans l'IFC | 02/03 | Question ouverte | Majeure | P1 | Corroboré | Moyenne | citation vérifiée |
| CCT-001 | Reservations : charge attribuee a deux lots differents (Gros oeuvre et CVC) | 02 Gros oeuvre / 07 CVC | Incohérence | Majeure | P1 | Corroboré | Élevée | citation vérifiée |
| SYN-002 | Raccord façade / acrotère / toiture sans lot ni quantité : la hauteur d'enduit de 6,50 m inclut-elle l'acrotère ? | 03 Façades / toiture non attribuée | Question ouverte | Majeure | P1 | Corroboré | Moyenne | citation vérifiée |
| SYN-003 | Existence d'un niveau R+1 : escalier, trémies et local technique CVC prescrits, mais aucun plan ni dalle correspondants | 02 Gros oeuvre / 07 CVC / architecture | Question ouverte | Majeure | P1 | À vérifier | Moyenne | citation vérifiée |
| SYN-004 | Réservations : charge contradictoire et plans de réservation sans lot 07 chiffré ni ligne au DPGF 02 | 02 Gros oeuvre / 07 CVC | Omission possible | Majeure | P1 | Corroboré | Moyenne | citation vérifiée |
| ENV-004 | Points singuliers de façade et interface menuiseries non décrits (appuis, tableaux, calfeutrement) | 03 Facades | Omission possible | Majeure | P2 | À vérifier | Moyenne | citation vérifiée |
| ARC-006 | Escalier et trémies prescrits au CCTP mais non représentés au plan RDC | 02 Gros oeuvre | Question ouverte | Modérée | P2 | À vérifier | Moyenne | citation vérifiée |
| ARC-007 | Fenêtres IFC de 2,5 x 1,2 et hauteur sous plafond de 2,50 m : disposition à clarifier | 03 / menuiseries | Question ouverte | Modérée | P2 | À vérifier | Faible | citation vérifiée |
| CCT-007 | Enduit sur 'facades maconnees' alors que le lot 02 decrit des voiles beton | 03 Facades / 02 Gros oeuvre | Question ouverte | Modérée | P2 | À vérifier | Moyenne | citation vérifiée |
| CCT-008 | Centrale double flux 'local technique du R+1' alors que les plans lus sont au RDC | 07 CVC | Question ouverte | Modérée | P2 | À vérifier | Faible | citation vérifiée |
| ENV-005 | Complexe de façade : support « maçonné » au CCTP, voile BA en coupe, pas d'isolation décrite | 03 Facades | Question ouverte | Modérée | P2 | À vérifier | Faible | citation vérifiée |

#### ARC-003 — Emprise 24,00 x 10,50 m (252 m2) contre salle et surface de plancher annoncées à 120 m2
- **Type** : Incohérence · **Gravité** : Critique · **Priorité** : P1 · **Statut** : Corroboré · **Confiance** : Moyenne
- **Lot / discipline** : 02 Gros oeuvre / transversal / architecture
- **Constat** : Les façades Nord/Sud sont cotées 24,00 m et Est/Ouest 10,50 m, soit 252 m2 d'emprise rectangulaire, alors que le plan nomme 'SALLE POLYVALENTE 120 m2' et que le CCTP, l'IFC et le DPGF retiennent 120 m2 pour la dalle haute, le dallage et le béton de propreté.
- **Preuve** (citation vérifiée) : D009 p.PDF 1 plan, libellés de façades et salle « SALLE POLYVALENTE 120 m2 » [citation_verifiee]; D009 p.PDF 1 libellé façade Nord « FACADE NORD - 24,00 m » [citation_verifiee]; D002 p.PDF 2 art. 2.6 « Surface de plancher : 120 m2. » [citation_verifiee]; D005 p.PDF 1 L8 poste 2.4 « Dallage sur terre-plein ép. 12 cm | m2 | 120 | 45 | 5040 » [citation_verifiee]
- **Calcul** : L x l ; L=24.0 m (D009 façade Nord), l=10.5 m (D009 façade Est/Ouest) => 252.0 m2 — vérification : recalcule_ok
- **Impact économique** : non quantifié : Aucun prix traité dans cette analyse (hors charte).
- **Impact technique** : Surface de plancher et emprise à distinguer (SDP, emprise, surface utile) ; la surface de la dalle n'est pas établie par les cotes lues.
- **Justification du statut** : confirmé par 1 vérificateur(s)
- **Contre-arguments** : 120 m2 peut désigner la seule salle polyvalente, avec d'autres locaux non représentés ; surface de plancher et emprise sont des notions distinctes. ; Le plan RDC peut contenir des locaux hors salle non légendés dans l'extrait ; le plan graphique ne les nomme pas.
- **Action recommandée** : Demander à l'architecte les cotes intérieures et le tableau de surfaces ; confirmer si le bâtiment ne comporte qu'une salle de 120 m2. — à solliciter : Architecte / maîtrise d'œuvre
- **Fusionné avec** : MET-006 (détecté par architecture, metres)

Dépend de : ARC-002 (corroboré), ECO-001 (corroboré)

#### ENV-003 — Aucune pièce de couverture/étanchéité alors que la coupe montre un acrotère
- **Type** : Omission possible · **Gravité** : Critique · **Priorité** : P1 · **Statut** : Corroboré · **Confiance** : Faible
- **Lot / discipline** : Non attribué (toiture) / enveloppe
- **Constat** : La coupe AA mentionne un acrotère de 0,60 m, ce qui suggère une toiture-terrasse, mais aucun CCTP, DPGF ou métré lu ne traite couverture, étanchéité, relevés, couvertines, évacuations pluviales ou isolation de toiture.
- **Preuve** (citation vérifiée) : D010 p.PDF 1 Coupe AA A-201, haut de façade « Acrotere h = 0,60 m » [citation_verifiee]; D001 p.PDF 1 Article 2 « - les CCTP des lots 02, 03 et 07 ; » [citation_verifiee]
- **Impact économique** : non quantifié : Aucune quantité ni prix de toiture dans le dossier.
- **Impact technique** : Étanchéité, relevés, protection de tête d'acrotère, évacuations EP et continuité d'isolation façade/toiture non définis.
- **Justification du statut** : confirmé par 1 vérificateur(s), pair indépendant
- **Contre-arguments** : Le dossier est un extrait (3 lots) : un lot couverture/étanchéité peut exister hors périmètre fourni ; Le lot Gros oeuvre peut inclure la dalle et l'acrotère (lecture non faite ici)
- **Action recommandée** : Confirmer l'existence et le lot de la couverture/étanchéité et de ses points singuliers ; sinon compléter le DCE. — à solliciter : Architecte / économiste MOE

Dépend de : ENV-005 (à vérifier)

#### SYN-001 — Voiles BA du lot 02 (210 m2) très inférieurs aux façades à enduire du lot 03 (448,5 m2 brut)
- **Type** : Incohérence · **Gravité** : Critique · **Priorité** : P1 · **Statut** : Corroboré · **Confiance** : Moyenne
- **Lot / discipline** : 02 Gros oeuvre / 03 Façades / synthese_interlots
- **Constat** : Le DPGF lot 02 chiffre 210 m2 de voiles BA, alors que le métré du lot 03 repose sur 448,5 m2 de façades brutes (avant déduction des baies) dont la coupe indique que le support est un voile BA. Les deux lots ne décrivent pas la même enveloppe ou l'un des deux est mal quantifié.
- **Preuve** (citation vérifiée) : D005 p.PDF 1 ligne 9, poste 2.5 « L9: 2.5 | Voiles BA ép. 18 cm | m2 | 210 | 95 | 19950 » [citation_verifiee]; D007 p.PDF 2 feuille Detail enduit, ligne 3 « L3: Nord | 24 | 6.5 | 156 » [citation_verifiee]; D007 p.PDF 2 feuille Detail enduit, ligne 5 « L5: Est | 10.5 | 6.5 | 68.25 » [citation_verifiee]; D002 p.PDF 2 art. 2.5 « Voiles en beton arme epaisseur 18 cm, parement soigne cote interieur. » [citation_verifiee]
- **Calcul** : S_facades_brutes - S_voiles ; S_facades_brutes=448.5 m2 (D007 feuille Detail enduit L3-L6 : 156+156+68,25+68,25), S_voiles=210 m2 (D005 L9) => 238.5 m2 — vérification : recalcule_ok
- **Impact économique** : non quantifié : Impact conditionnel : on ne sait pas si l'écart est une erreur de quantité ou une différence de périmètre ; à titre indicatif 238,5 x 95 = 22 657,5 EUR HT si l'écart correspondait à des voiles non chiffrés. Non retenu comme montant.
- **Justification du statut** : confirmé par 1 vérificateur(s)
- **Contre-arguments** : La hauteur de 6,50 m n'est pas établie (ARC-004, MET-005) ; avec 2,50 m de hauteur sous plafond seule connue, les surfaces ne sont pas comparables. ; Les voiles peuvent ne pas couvrir tout le périmètre.
- **Action recommandée** : Faire reprendre par le métreur le calcul des voiles du lot 02 sur la même base géométrique que les façades du lot 03. — à solliciter : Métreur / économiste MOE

Dépend de : ARC-003 (corroboré), CCT-007 (à vérifier), ENV-005 (à vérifier), MET-005 (corroboré), MET-007 (à vérifier)

#### ARC-001 — Plan A-101 : 14 fenêtres à l'indice A, 12 à l'indice B (versions concurrentes)
- **Type** : Incohérence · **Gravité** : Majeure · **Priorité** : P1 · **Statut** : Corroboré · **Confiance** : Élevée
- **Lot / discipline** : Transversal (03 Façades, menuiseries) / architecture
- **Constat** : A-101 indice A annonce 14 fenêtres (F1 à F14), l'indice B en annonce 12 et indique la suppression de F13 et F14 en façade Est. Aucune pièce lue ne désigne l'indice applicable ; la maquette IFC (12 fenêtres) et le DPGF/métré lot 03 (12 appuis) sont alignés sur 12.
- **Preuve** (citation vérifiée) : D008 p.PDF 1 cartouche « Fenetres : 14 (F1 a F14) » [citation_verifiee]; D009 p.PDF 1 cartouche « Modif. ind. B : suppression F13 et F14 (facade Est) » [citation_verifiee]; D012 IFCWINDOW #100 à #111, F1 à F12 [sans_citation]; D006 p.PDF 1 L7 poste 3.4 « Appuis de fenêtres béton préfabriqués | u | 12 | 95 | 1140 » [citation_verifiee]
- **Impact économique** : non quantifié : Aucun prix traité dans cette analyse (hors charte).
- **Impact technique** : Façade Est : présence ou non de 2 baies ; incidence sur appuis (lot 03) et déduction d'enduit.
- **Justification du statut** : confirmé par 1 vérificateur(s)
- **Contre-arguments** : L'indice B plus récent peut remplacer l'indice A, mais aucune pièce du dossier ne l'écrit.
- **Action recommandée** : Faire confirmer par la maîtrise d'œuvre l'indice A-101 en vigueur et diffuser un bordereau d'indices. — à solliciter : Architecte / maîtrise d'œuvre

Dépend de : MET-004 (corroboré)

#### ARC-002 — Dalle haute RDC : 18 cm (coupe, IFC) contre 20 cm (CCTP, DPGF)
- **Type** : Incohérence · **Gravité** : Majeure · **Priorité** : P1 · **Statut** : Corroboré · **Confiance** : Élevée
- **Lot / discipline** : 02 Gros oeuvre / architecture
- **Constat** : La coupe A-201 indice A et la maquette IFC donnent une dalle haute RDC de 18 cm ; le CCTP lot 02 art. 2.6 prescrit 20 cm et le DPGF lot 02 ligne 2.6 chiffre 24 m3 (= 120 m2 x 0,20 m).
- **Preuve** (citation vérifiée) : D010 p.PDF 1 coupe, légende dalle haute « Dalle haute RDC ep. 18 cm » [citation_verifiee]; D002 p.PDF 2 art. 2.6 « Dalle pleine en beton arme epaisseur 20 cm, coulee en place. » [citation_verifiee]; D005 p.PDF 1 L10 poste 2.6 « Dalle haute RDC BA ép. 20 cm | m3 | 24 | 285 | 6840 » [citation_verifiee]; D012 #20 IFCSLAB DH-RDC, #22 Width 0.18, #23 NetVolume 21.6 [sans_citation]
- **Calcul** : S x (e_cctp - e_coupe) ; S=120 m2 (D002 art. 2.6 / D012 #21), e_cctp=0.2 m (D002 art. 2.6), e_coupe=0.18 m (D010) => 2.4 m3 — vérification : recalcule_ok
- **Impact économique** : 684,00 € HT (2,4 m3 x PU DPGF 285 EUR/m3 (D005 l.10))
- **Impact technique** : Épaisseur de dalle porteuse à confirmer ; calcul de structure non vérifié ici.
- **Justification du statut** : confirmé par 1 vérificateur(s), pair indépendant
- **Contre-arguments** : La coupe est indice A du 12/03/2026 : pas de preuve qu'elle soit postérieure ou antérieure au CCTP (CCTP non daté). ; Le plan de structure cité par le CCTP n'est pas au dossier ; il pourrait fixer l'épaisseur. ; La coupe est a l'indice A et pourrait etre non a jour ; La coupe est un document architecte, la dalle peut être définie par les plans de structure absents du dossier ; Aucun ordre de priorité des pièces n'est écrit dans le CCAP extrait
- **Action recommandée** : Faire arbitrer l'épaisseur par la maîtrise d'œuvre et l'ingénieur structure, puis aligner coupe, IFC, CCTP et DPGF. — à solliciter : Architecte et bureau d'études structure
- **Fusionné avec** : MET-003, CCT-002, ECO-004 (détecté par architecture, cctp, economie, metres)

Dépend de : ARC-003 (corroboré), D002 (identifiant inconnu), D005 (identifiant inconnu), D010 (identifiant inconnu)

#### ARC-004 — Hauteurs : 6,50 m de façade au métré, aucune hauteur totale écrite sur la coupe ; niveau R+1 à 3,20 m dans l'IFC
- **Type** : Question ouverte · **Gravité** : Majeure · **Priorité** : P1 · **Statut** : Corroboré · **Confiance** : Moyenne
- **Lot / discipline** : 02/03 / architecture
- **Constat** : La coupe A-201 ne porte que la hauteur sous plafond (2,50 m), l'épaisseur de dalle et l'acrotère (0,60 m) ; aucune hauteur totale n'est cotée. Le métré retient 6,50 m de hauteur de façade ; l'IFC place un niveau R+1 à 3,2 (sans élément R+1 rattaché). Les hauteurs ne peuvent être rapprochées avec les cotes écrites.
- **Preuve** (citation vérifiée) : D010 p.PDF 1 légendes de la coupe « Hauteur sous plafond 2,50 m » [citation_verifiee]; D007 p.PDF 2 feuille Detail enduit, L3 « Nord | 24 | 6.5 | 156 » [citation_verifiee]; D012 #11 IFCBUILDINGSTOREY R+1 3.2 [sans_citation]
- **Calcul** : HSP + e_dalle + h_acrotere ; HSP=2.5 m (D010), e_dalle=0.18 m (D010), h_acrotere=0.6 m (D010) => 3.28 m — vérification : recalcule_ok
- **Impact économique** : non quantifié : Aucun prix traité dans cette analyse (hors charte).
- **Impact technique** : Hauteur totale du bâtiment et nombre de niveaux non établis.
- **Justification du statut** : confirmé par 1 vérificateur(s), pair indépendant
- **Contre-arguments** : La somme 3,28 m ignore la hauteur du dallage, du vide sanitaire éventuel et de la pente de toiture : elle n'est pas une cote de hauteur totale.
- **Action recommandée** : Demander la cote de hauteur de façade (sol fini / acrotère) et confirmer l'existence ou non d'un R+1. — à solliciter : Architecte

Dépend de : MET-005 (corroboré)

#### CCT-001 — Reservations : charge attribuee a deux lots differents (Gros oeuvre et CVC)
- **Type** : Incohérence · **Gravité** : Majeure · **Priorité** : P1 · **Statut** : Corroboré · **Confiance** : Élevée
- **Lot / discipline** : 02 Gros oeuvre / 07 CVC / contractuel
- **Constat** : Le CCTP Lot 02 (art. 2.4) met les reservations et tremies des voiles et planchers beton a la charge des lots techniques, alors que le CCTP Lot 07 (art. 7.3) les met a la charge du lot Gros oeuvre.
- **Preuve** (citation vérifiée) : D002 p.PDF 1 Article 2.4 - Reservations « Les reservations et tremies dans les voiles et planchers beton sont a la » [citation_verifiee]; D002 p.PDF 1 Article 2.4 - Reservations (suite) « charge des lots techniques, qui en assurent le reperage et le calfeutrement. » [citation_verifiee]; D004 p.PDF 1 Article 7.3 - Reservations « les voiles et planchers sont a la charge du lot Gros oeuvre, sur plans de » [citation_verifiee]; D002 p.PDF 1 Article 2.4 « a la
charge des lots techniques » [citation_verifiee]
- **Impact économique** : non quantifié : Aucun prix de reservation isole dans les DPGF disponibles ; non quantifiable
- **Impact technique** : Reservations gaines CVC : responsable non defini, risque de percements ulterieurs en voiles BA
- **Justification du statut** : confirmé par 1 vérificateur(s), pair indépendant
- **Contre-arguments** : Le CCTP 02 vise les 'lots techniques' en general et le 7.3 une precision specifique CVC ; mais aucune clause ecrite de priorite ne permet de trancher ; Le CCAP extrait ne précise aucun ordre de priorité entre les CCTP ; rien n'indique lequel prévaut ; Les plans de réservation ne sont pas au dossier
- **Action recommandée** : Arbitrer par la MOE et harmoniser les deux CCTP (un seul responsable, un seul calfeutrement) — à solliciter : Maitrise d'oeuvre (architecte / BET)
- **Fusionné avec** : ECO-006 (détecté par cctp, economie)

Dépend de : D002 (identifiant inconnu), D004 (identifiant inconnu)

#### SYN-002 — Raccord façade / acrotère / toiture sans lot ni quantité : la hauteur d'enduit de 6,50 m inclut-elle l'acrotère ?
- **Type** : Question ouverte · **Gravité** : Majeure · **Priorité** : P1 · **Statut** : Corroboré · **Confiance** : Moyenne
- **Lot / discipline** : 03 Façades / toiture non attribuée / synthese_interlots
- **Constat** : La coupe montre un acrotère de 0,60 m ; le CCAP ne liste que les lots 02, 03 et 07 ; le métré d'enduit applique 6,50 m à chaque façade sans dire si l'acrotère et ses retours sont compris. Ni couvertine, ni relevé, ni traitement du raccord enduit/étanchéité n'est attribué.
- **Preuve** (citation vérifiée) : D010 p.PDF 1 Coupe AA A-201 « Acrotere h = 0,60 m » [citation_verifiee]; D001 p.PDF 1 Article 2 « - les CCTP des lots 02, 03 et 07 ; » [citation_verifiee]; D007 p.PDF 2 feuille Detail enduit, ligne 4 « L4: Sud | 24 | 6.5 | 156 » [citation_verifiee]; D003 p.PDF 1 Article 3.1 « Echafaudages de pied conformes, sur toute la hauteur des facades. » [citation_verifiee]
- **Impact économique** : non évalué
- **Justification du statut** : confirmé par pair indépendant
- **Action recommandée** : Faire trancher par l'architecte le lot porteur de l'acrotère et du raccord enduit/étanchéité, puis par le métreur la hauteur d'enduit. — à solliciter : Architecte / MOE

Dépend de : ARC-004 (corroboré), ENV-003 (corroboré), ENV-004 (à vérifier), MET-005 (corroboré)

#### SYN-003 — Existence d'un niveau R+1 : escalier, trémies et local technique CVC prescrits, mais aucun plan ni dalle correspondants
- **Type** : Question ouverte · **Gravité** : Majeure · **Priorité** : P1 · **Statut** : À vérifier · **Confiance** : Moyenne
- **Lot / discipline** : 02 Gros oeuvre / 07 CVC / architecture / synthese_interlots
- **Constat** : Le CCTP 07 place la centrale au R+1 et le CCTP 02 prescrit escalier, trémies et garde-corps, l'IFC contient un niveau R+1 ; le plan A-101 est limité au RDC et la coupe ne montre qu'une dalle haute RDC. Les pièces ne permettent pas de dire si un R+1 existe ni qui réalise l'escalier et le plancher correspondants.
- **Preuve** (citation vérifiée) : D004 p.PDF 2 Article 7.4 « Centrale installee dans le local technique du R+1. » [citation_verifiee]; D002 p.PDF 2 art. 2.7 « Escalier interieur en beton arme coule en place. » [citation_verifiee]; D002 p.PDF 2 art. 2.8 « Les garde-corps des escaliers et tremies seront realises selon detail D12. » [citation_verifiee]; D009 p.PDF 1 plan RDC, titre « Plan RDC - A-101 » [citation_verifiee]
- **Impact économique** : non évalué
- **Justification du statut** : non vérifié de façon indépendante
- **Action recommandée** : Demander à l'architecte de confirmer l'existence et la définition du R+1 (plan, coupe, dalle). — à solliciter : Architecte

Dépend de : ARC-004 (corroboré), ARC-005 (corroboré), ARC-006 (à vérifier), CCT-008 (à vérifier), ECO-005 (corroboré)

#### SYN-004 — Réservations : charge contradictoire et plans de réservation sans lot 07 chiffré ni ligne au DPGF 02
- **Type** : Omission possible · **Gravité** : Majeure · **Priorité** : P1 · **Statut** : Corroboré · **Confiance** : Moyenne
- **Lot / discipline** : 02 Gros oeuvre / 07 CVC / synthese_interlots
- **Constat** : Au-delà de la contradiction CCT-001, le CCTP 07 fait dépendre les réservations de plans fournis par le lot 07, alors que le CCAP ne liste aucun DPGF du lot 07 et que le DPGF 02 ne comporte aucune ligne de réservations ni calfeutrement. Aucun lot n'est donc chiffré pour cette prestation, quel que soit l'arbitrage.
- **Preuve** (citation vérifiée) : D002 p.PDF 1 Article 2.4 « charge des lots techniques, qui en assurent le reperage et le calfeutrement. » [citation_verifiee]; D004 p.PDF 1 Article 7.3 « les voiles et planchers sont a la charge du lot Gros oeuvre, sur plans de » [citation_verifiee]; D001 p.PDF 1 Article 2 « - les DPGF des lots 02 et 03 ; » [citation_verifiee]
- **Impact économique** : non évalué
- **Justification du statut** : confirmé par pair indépendant
- **Action recommandée** : Faire arbitrer la charge, puis intégrer la ligne dans le DPGF du lot retenu. — à solliciter : Maître d'oeuvre / économiste

Dépend de : CCT-001 (corroboré), CCT-004 (à vérifier), ECO-007 (à vérifier)

#### ENV-004 — Points singuliers de façade et interface menuiseries non décrits (appuis, tableaux, calfeutrement)
- **Type** : Omission possible · **Gravité** : Majeure · **Priorité** : P2 · **Statut** : À vérifier · **Confiance** : Moyenne
- **Lot / discipline** : 03 Facades / enveloppe
- **Constat** : Le CCTP du lot 03 décrit les appuis béton en une ligne et ne traite ni tableaux/ébrasements, ni joints périphériques, ni pose et étanchéité des appuis, ni lot de fourniture et pose des menuiseries ; seule la protection des menuiseries est attribuée au lot 03.
- **Preuve** (citation vérifiée) : D003 p.2 Article 3.4 « Appuis prefabriques en beton, un par fenetre. » [citation_verifiee]; D003 p.1 Article 3.3 « La protection des menuiseries exterieures pendant les travaux » [citation_verifiee]; D006 p.PDF 1 ligne 7, art. 3.4 « L7: 3.4 | Appuis de fenêtres béton préfabriqués | u | 12 | 95 | 1140 » [citation_verifiee]
- **Impact économique** : non quantifié : Aucune base de prix pour tableaux ou calfeutrement dans les pièces.
- **Impact technique** : Risque d'infiltration aux appuis et tableaux si l'interface n'est pas attribuée.
- **Justification du statut** : non vérifié de façon indépendante
- **Contre-arguments** : Les tableaux peuvent être inclus implicitement dans l'enduit sur l'ensemble des façades ; Le calfeutrement relève habituellement du lot menuiseries, hors dossier
- **Action recommandée** : Faire préciser dans le CCTP la limite de prestations enduit/appuis/menuiseries (tableaux, joints, pose des appuis) et le lot concerné. — à solliciter : Rédacteur CCTP

Dépend de : MET-004 (corroboré)

#### ARC-006 — Escalier et trémies prescrits au CCTP mais non représentés au plan RDC
- **Type** : Question ouverte · **Gravité** : Modérée · **Priorité** : P2 · **Statut** : À vérifier · **Confiance** : Moyenne
- **Lot / discipline** : 02 Gros oeuvre / architecture
- **Constat** : Le CCTP lot 02 prévoit un escalier intérieur en béton armé et des garde-corps d'escaliers et de trémies ; ni A-101 (indices A et B) ni l'IFC ne représentent d'escalier ou de trémie, et la coupe n'en montre pas non plus.
- **Preuve** (citation vérifiée) : D002 p.PDF 2 art. 2.7 « Escalier interieur en beton arme coule en place. » [citation_verifiee]; D009 p.PDF 1 plan RDC, observation graphique (aucun escalier ni trémie dessiné) [sans_citation]; D012 DATA, aucun IFCSTAIR [sans_citation]
- **Impact économique** : non quantifié : Aucun prix traité dans cette analyse (hors charte).
- **Impact technique** : Localisation, volée, trémie et réservations non définies ; lien possible avec un niveau R+1 (voir ARC-004).
- **Justification du statut** : non vérifié de façon indépendante
- **Contre-arguments** : Le plan peut être un schéma et l'escalier figurer sur un plan d'autre niveau non fourni.
- **Action recommandée** : Faire fournir le plan de l'escalier et des trémies, ou confirmer leur absence au projet. — à solliciter : Architecte

Dépend de : ARC-004 (corroboré), ARC-005 (corroboré)

#### ARC-007 — Fenêtres IFC de 2,5 x 1,2 et hauteur sous plafond de 2,50 m : disposition à clarifier
- **Type** : Question ouverte · **Gravité** : Modérée · **Priorité** : P2 · **Statut** : À vérifier · **Confiance** : Faible
- **Lot / discipline** : 03 / menuiseries / architecture
- **Constat** : L'IFC donne à chaque fenêtre les valeurs 2.5 et 1.2 et le métré déduit 12 x 1,20 x 2,50 ; la hauteur sous plafond de la coupe est également de 2,50 m. Si 2,5 m est la hauteur de baie, elle égalerait la hauteur sous plafond, sans allège ni linteau visibles. Aucune cote de baie ni d'allège n'est écrite sur plans ou coupe.
- **Preuve** (citation vérifiée) : D012 #100 IFCWINDOW F1 [sans_citation]; D007 p.PDF 2 L7 « Déduction baies (12 x 1,20 x 2,50) » [citation_verifiee]; D010 p.PDF 1 légende HSP « Hauteur sous plafond 2,50 m » [citation_verifiee]
- **Impact économique** : non quantifié : Aucun prix traité dans cette analyse (hors charte).
- **Impact technique** : Constructibilité : baie sur toute la hauteur sous plafond sans linteau ni allège visible.
- **Justification du statut** : non vérifié de façon indépendante
- **Contre-arguments** : Les attributs IFC peuvent être inversés ou la hauteur de baie ne pas se mesurer à partir de la dalle.
- **Action recommandée** : Demander le tableau des baies (largeur, hauteur, allège) à l'architecte. — à solliciter : Architecte

Dépend de : MET-008 (à vérifier)

#### CCT-007 — Enduit sur 'facades maconnees' alors que le lot 02 decrit des voiles beton
- **Type** : Question ouverte · **Gravité** : Modérée · **Priorité** : P2 · **Statut** : À vérifier · **Confiance** : Moyenne
- **Lot / discipline** : 03 Facades / 02 Gros oeuvre / enveloppe
- **Constat** : Le CCTP 03 vise des facades maconnees, alors que le CCTP 02 ne decrit que des voiles BA et aucune maconnerie n'apparait dans les pieces lues.
- **Preuve** (citation vérifiée) : D003 p.PDF 1 Article 3.2 - Enduit monocouche « sur l'ensemble des facades maconnees. Quantites : voir metre joint au dossier. » [citation_verifiee]; D002 p.PDF 2 Article 2.5 - Voiles « Voiles en beton arme epaisseur 18 cm, parement soigne cote interieur. » [citation_verifiee]
- **Impact économique** : non quantifié : Non chiffrable
- **Impact technique** : Preparation du support (BA ou maconnerie) a definir
- **Justification du statut** : non vérifié de façon indépendante
- **Contre-arguments** : 'Maconnees' peut etre un terme generique
- **Action recommandée** : Preciser la nature du support exterieur et le lot responsable — à solliciter : Architecte / BET

Dépend de : D002 (identifiant inconnu), D003 (identifiant inconnu)

#### CCT-008 — Centrale double flux 'local technique du R+1' alors que les plans lus sont au RDC
- **Type** : Question ouverte · **Gravité** : Modérée · **Priorité** : P2 · **Statut** : À vérifier · **Confiance** : Faible
- **Lot / discipline** : 07 CVC / cvc_plomberie
- **Constat** : Le CCTP 07 situe la centrale au R+1 ; aucun plan R+1 n'est fourni et le DPGF 02 ne chiffre qu'une dalle haute RDC.
- **Preuve** (citation vérifiée) : D004 p.PDF 2 Article 7.4 - Centrale double flux « Centrale installee dans le local technique du R+1. » [citation_verifiee]
- **Impact économique** : non quantifié : Non chiffrable
- **Impact technique** : Emplacement, structure support et reseaux de la centrale non verifiables
- **Justification du statut** : non vérifié de façon indépendante
- **Contre-arguments** : Le dossier fourni est un extrait
- **Action recommandée** : Faire confirmer le niveau et le local d'implantation de la centrale — à solliciter : Architecte / BET fluides

Dépend de : D004 (identifiant inconnu)

#### ENV-005 — Complexe de façade : support « maçonné » au CCTP, voile BA en coupe, pas d'isolation décrite
- **Type** : Question ouverte · **Gravité** : Modérée · **Priorité** : P2 · **Statut** : À vérifier · **Confiance** : Faible
- **Lot / discipline** : 03 Facades / enveloppe
- **Constat** : Le CCTP applique l'enduit aux « facades maconnees » alors que la coupe AA indique un voile BA de 18 cm ; aucune isolation de façade (ITE ou ITI), aucun traitement de continuité avec la dalle ou l'acrotère n'est décrit dans les pièces lues.
- **Preuve** (citation vérifiée) : D003 p.1 Article 3.2 « sur l'ensemble des facades maconnees. » [citation_verifiee]; D010 p.PDF 1 Coupe AA A-201 « Voile BA ep. 18 cm » [citation_verifiee]
- **Impact économique** : non quantifié : Pas de données de prix.
- **Impact technique** : Continuité d'isolation et ponts thermiques aux jonctions non vérifiables ; performance thermique hors périmètre.
- **Justification du statut** : non vérifié de façon indépendante
- **Contre-arguments** : Le voile BA peut être limité à une zone, le reste étant maçonné
- **Action recommandée** : Faire préciser par l'architecte la nature des supports de façade, l'isolation éventuelle et le système d'enduit. — à solliciter : Architecte

Dépend de : ENV-003 (corroboré)


## Décisions à prendre et échéances

| Constat | Décision attendue | Échéance | Statut |
|---|---|---|---|
| ARC-003 | Demander à l'architecte les cotes intérieures et le tableau de surfaces ; confirmer si le bâtiment ne comporte qu'une salle de 120 m2. | avant consultation / signature | Corroboré |
| ENV-003 | Confirmer l'existence et le lot de la couverture/étanchéité et de ses points singuliers ; sinon compléter le DCE. | avant consultation | Corroboré |
| SYN-001 | Faire reprendre par le métreur le calcul des voiles du lot 02 sur la même base géométrique que les façades du lot 03. | avant consultation / signature du marché | Corroboré |
| ARC-001 | Faire confirmer par la maîtrise d'œuvre l'indice A-101 en vigueur et diffuser un bordereau d'indices. | avant consultation / signature | Corroboré |
| ARC-002 | Faire arbitrer l'épaisseur par la maîtrise d'œuvre et l'ingénieur structure, puis aligner coupe, IFC, CCTP et DPGF. | avant consultation / signature | Corroboré |
| ARC-004 | Demander la cote de hauteur de façade (sol fini / acrotère) et confirmer l'existence ou non d'un R+1. | avant consultation / signature | Corroboré |
| ARC-005 | Demander la transmission du carnet DET-01 à DET-15. | avant consultation / signature | Corroboré |
| CCT-001 | Arbitrer par la MOE et harmoniser les deux CCTP (un seul responsable, un seul calfeutrement) | avant consultation des entreprises | Corroboré |
| ECO-002 | Faire arbitrer la quantité d'enduit par l'économiste et le métreur, puis aligner DPGF et métré. | avant consultation (quantité contractuelle du DPGF) | Corroboré |
| ECO-005 | Faire ajouter ou justifier des postes escalier et garde-corps (ou indiquer leur rattachement) dans le DPGF Lot 02. | avant consultation | Corroboré |
| MET-004 | Faire confirmer l'indice en vigueur de A-101 et l'indiquer sur le métré. | avant consultation | Corroboré |
| MET-005 | Obtenir la cote de hauteur de façade (avec ou sans acrotère) et la tracer dans le métré. | avant consultation | Corroboré |
| SYN-002 | Faire trancher par l'architecte le lot porteur de l'acrotère et du raccord enduit/étanchéité, puis par le métreur la hauteur d'enduit. | avant consultation | Corroboré |
| SYN-003 | Demander à l'architecte de confirmer l'existence et la définition du R+1 (plan, coupe, dalle). | avant consultation | À vérifier |
| SYN-004 | Faire arbitrer la charge, puis intégrer la ligne dans le DPGF du lot retenu. | avant consultation | Corroboré |
| CCT-005 | Fournir l'article de priorite des pieces et preciser l'indice des plans contractuels | avant signature | À vérifier |
| ECO-001 | Faire corriger la ligne 2.4 par l'économiste (confirmer quantité et PU) puis recalculer sous-total, total, TVA et TTC. | avant consultation / mise au point du DPGF | Corroboré |
| ENV-004 | Faire préciser dans le CCTP la limite de prestations enduit/appuis/menuiseries (tableaux, joints, pose des appuis) et le lot concerné. | avant exécution des enduits | À vérifier |
| ARC-006 | Faire fournir le plan de l'escalier et des trémies, ou confirmer leur absence au projet. | avant exécution des ouvrages concernés | À vérifier |
| ARC-007 | Demander le tableau des baies (largeur, hauteur, allège) à l'architecte. | avant exécution des ouvrages concernés | À vérifier |
| CCT-004 | Faire verifier par l'economiste que ces ouvrages sont inclus ou a ajouter | avant mise au point du marche | À vérifier |
| CCT-007 | Preciser la nature du support exterieur et le lot responsable | avant consultation | À vérifier |
| CCT-008 | Faire confirmer le niveau et le local d'implantation de la centrale | avant execution du lot 07 | À vérifier |
| ECO-007 | Faire préciser dans le DPGF/CCTP si ces prestations sont incluses dans les prix unitaires. | avant exécution des ouvrages concernés | À vérifier |
| ENV-005 | Faire préciser par l'architecte la nature des supports de façade, l'isolation éventuelle et le système d'enduit. | avant exécution des enduits | À vérifier |
| MET-007 | Demander le métré détaillé du lot 02 et les plans de structure. | avant exécution / mise au point du marché | À vérifier |
| MET-008 | Faire écrire la convention de métré dans le CCTP et vérifier les dimensions de baie. | avant mise au point du marché | À vérifier |
| ARC-008 | Faire retirer la mention du CCTP et en identifier l'origine. | à suivre | Corroboré |
