# France and Greece: Cybersecurity and GDPR Compliance Guidelines

**Project:** EyeNet Vision / PPL Meta Platform  
**Date:** 17 September 2026  
**Scope:** Official French and Greek guidelines, checklists, and control lists for cybersecurity and GDPR-compliant software / services.

> This is an informational source map, not legal advice. GDPR compliance sits on the **controller** (the customer) and, for processors, on the **service provider**. Neither France nor Greece publishes a whitelist of “GDPR-compliant software.”

**Related internal documents**

- Jurisdiction and use-case law: [`docs/product/legal/Συνοπτική_Νομοθεσία_Προσωπικών_Δεδομένων_Ελλάδα_ΕΕ_ΗΠΑ.md`](../product/legal/Συνοπτική_Νομοθεσία_Προσωπικών_Δεδομένων_Ελλάδα_ΕΕ_ΗΠΑ.md)
- EyeNet executive overlay (Presence, triggers, keys, bootstrap, mesh): [`eyenet-executive-compliance-guide.md`](eyenet-executive-compliance-guide.md)

---

## 1. What exists — and what does not

There is **no official French or Greek catalogue of “GDPR-compliant software.”** What both countries publish is:

1. GDPR implementation checklists and DPIA tools
2. Cybersecurity control lists / handbooks
3. In France only: a catalogue of **ANSSI-certified / qualified security products and services** (cybersecurity qualification, not GDPR certification)

On-premises processing helps (fewer transfers, local control), but it does not by itself make a product GDPR-certified.

| Need | France | Greece |
|---|---|---|
| GDPR how-to list | CNIL 4 steps + TPE/PME checklist | HDPA 10 steps + byDesign toolkit |
| Security-of-personal-data list | CNIL 25-fiche 2024 guide | HDPA guide + Art. 32 GDPR; no equally detailed national security-of-data guide |
| Cyber hygiene list | ANSSI 42 measures | NCSA Cybersecurity Handbook (18 families) |
| Binding cyber controls if NIS2-in-scope | Transposition still pending; use ANSSI NIS2 pack | **KYA 1689/2025 (22 requirements)** already in force |
| Official product / service catalogue | **ANSSI certified/qualified catalogue** + SecNumCloud | No equivalent public product catalogue |
| Video / face / analytics | CNIL “caméras augmentées” + Art. 9 | HDPA Directive 1/2011 + EDPB 3/2019 + Art. 9 |

---

## 2. France

**Authorities**

- GDPR / privacy: [CNIL](https://www.cnil.fr)
- Cybersecurity: [ANSSI / cyber.gouv.fr](https://cyber.gouv.fr) and [MesServicesCyber](https://messervices.cyber.gouv.fr)
- Law: GDPR + *Loi Informatique et Libertés*

### 2.1 GDPR / privacy (CNIL)

#### Operational checklist

1. [RGPD : les premières étapes](https://www.cnil.fr/fr/passer-laction/rgpd-les-premieres-etapes) — official 4-step pack:
   - Register of processing activities
   - Data minimisation / retention
   - Information notices + data-subject rights (1-month SLA)
   - Security + 72-hour breach notification
2. [TPE/PME GDPR checklist (PDF)](https://www.cnil.fr/sites/cnil/files/atoms/files/check-list_rgpd_pour_les_tpe-pme.pdf)
3. [Documenter la conformité](https://www.cnil.fr/fr/documenter-la-conformite) — what you must be able to show: register, DPIAs, SCCs/BCRs, notices, processor contracts, consent proofs, incident procedures
4. [CNIL PIA / AIPD software](https://www.cnil.fr/en/open-source-pia-software-helps-carry-out-data-protection-impact-assessment) — official DPIA tool
5. CNIL–Bpifrance SME guide, linked from the same “premières étapes” page

#### Security of personal data (Art. 32 GDPR)

CNIL uses this as its **audit reference**:

- [Guide de la sécurité des données personnelles 2024](https://www.cnil.fr/fr/guide-de-la-securite-des-donnees-personnelles-nouvelle-edition-2024)
- [PDF of the 2024 guide](https://www.cnil.fr/sites/cnil/files/2024-03/cnil_guide_securite_personnelle_2024.pdf)
- [Matching checklist PDF](https://cnil-d10.cnil.fr/sites/cnil/files/2024-03/guide_securite_donnees_personnelles_checklist.pdf)
- English landing page: [Practice guide for the security of personal data: 2024 edition](https://www.cnil.fr/en/practice-guide-security-personal-data-2024-edition)

The 2024 guide has **25 factsheets**. Those that map to software / services:

| # | Topic |
|---|---|
| 1 | Security governance |
| 2–5 | Users, authentication, access rights |
| 6–11 | Workstations, mobile, network, servers, websites, development |
| 14–19 | Processors, maintenance, logging, backups, continuity, incidents |
| 20 | Risk analysis |
| 21 | Encryption / hashing / signature |
| 22 | Cloud |
| 23 | Mobile apps |
| 24 | Artificial intelligence |
| 25 | APIs |

Changelog of successive editions: [Suivi des modifications](https://www.cnil.fr/fr/modifications-guide-de-la-securite-des-donnees-personnelles)

#### Video / biometrics

Highly relevant for EyeNet. CNIL splits **anonymous / aggregate video analytics** from **facial recognition**. Face recognition is biometric (Art. 9 GDPR): prohibited by default.

- [Caméras « augmentées » ou algorithmiques dans l’espace public](https://www.cnil.fr/fr/cameras-augmentees-espaces-publics)
- [Reconnaissance faciale dans les aéroports](https://www.cnil.fr/fr/reconnaissance-faciale-dans-les-aeroports-quels-enjeux-et-quels-grands-principes-respecter)
- [Guide RGPD vidéo — collectivités territoriales (PDF)](https://cnil.fr/sites/cnil/files/2024-11/guide_rgpd_video_collectivites_territoriales.pdf)

### 2.2 Cybersecurity (ANSSI)

#### Baseline for any organisation

- [Guide d’hygiène informatique — 42 measures](https://messervices.cyber.gouv.fr/guides/guide-dhygiene-informatique) ([PDF](https://messervices.cyber.gouv.fr/documents-guides/guide_hygiene_informatique_anssi.pdf))
- [EBIOS Risk Manager](https://messervices.cyber.gouv.fr/guides/la-methode-ebios-risk-manager-le-guide) — official French risk method
- [MFA / password recommendations](https://messervices.cyber.gouv.fr/documents-guides/anssi-guide-authentification_multifacteur_et_mots_de_passe.pdf) (joint ANSSI + CNIL)
- [Secure administration of IT systems](https://messervices.cyber.gouv.fr/documents-guides/anssi-guide-admin_securisee_si_v3-0.pdf)
- [RGS 2.0 documents](https://cyber.gouv.fr/reglementation/reglementation-identite-confiance-numerique/securite-echanges-voie-electronique/referentiel-general-de-securite/documents-referentiel-general-de-securite/) — mainly public administrations and trust services
- SME / incident help: [cybermalveillance.gouv.fr](https://www.cybermalveillance.gouv.fr)

#### If selling or hosting security products or cloud in France

- [Catalogue of ANSSI-certified / qualified products and services](https://cyber.gouv.fr/offre-de-service/solutions-certifiees-et-qualifiees/services-de-securite-evalue/decouvrir-les-solutions-certifiees-qualifiees/) — closest official “approved software / services” list. Covers CC/CSPN products, SecNumCloud, qualified audits, incident response, etc. **Not a GDPR certification.**
- [SecNumCloud](https://cyber.gouv.fr/enjeux-technologiques/cloud/) — French trusted-cloud qualification for sensitive data

#### NIS2 (essential / important entities)

France had **not finished transposing NIS2** as of September 2026 (EU infringement open). Prepare against the ANSSI pack anyway:

- [NIS2 hub](https://messervices.cyber.gouv.fr/nis2)
- Core duties once in force: register with ANSSI, implement risk-management measures, report significant incidents
- Expected sanctions (directive maxima): up to 10 M€ or 2% worldwide turnover (essential entities); 7 M€ or 1.4% (important entities)

---

## 3. Greece

**Authorities**

- GDPR / privacy: [ΑΠΔΠΧ / Hellenic DPA](https://www.dpa.gr)
- Cybersecurity: [Εθνική Αρχή Κυβερνοασφάλειας / NCSA](https://cyber.gov.gr)
- Laws: GDPR + **Ν. 4624/2019** (data protection) + **Ν. 5160/2024** (NIS2)

### 3.1 GDPR / privacy (ΑΠΔΠΧ)

#### Operational checklist

1. [Συμμόρφωση με ΓΚΠΔ — official 10-step guide](https://www.dpa.gr/el/foreis/odigos_gkpd)
2. [byDesign SME toolkit](https://www.dpa.gr/el/byDesign_toolkit) — 10-question wizard that generates templates (policies, notices, RoPA, rights, breach procedures)
3. [DPIA “must-do” list](https://www.dpa.gr/el/enimerwtiko/prakseisArxis/katalogos-me-ta-eidi-ton-praxeon-epexergasias-poy-ypokeintai-stin) — Decision 65/2018 ([PDF](https://www.dpa.gr/sites/default/files/2019-10/article_35_dpia_list_gr_2.pdf)). Video surveillance, systematic monitoring, biometrics, and large-scale special-category data typically trigger a DPIA.
4. [Essential DPIA completeness criteria (PDF)](https://www.dpa.gr/sites/default/files/2020-12/ESSENTIAL_STANDARD_CRITERIA_DPIA_0.pdf)

#### HDPA 10 steps (the actual compliance list)

1. Awareness / readiness and risk strategy
2. Record of processing activities
3. Ongoing lawfulness and rights checks
4. Consent review
5. Update policies and rights-handling procedures
6. DPIA
7. Appoint a DPO if required
8. Breach detection, logging, HDPA notification
9. Lead supervisory authority if operating in several Member States
10. Transfers outside the EU (SCCs, BCRs, etc.)

Greece does **not** publish a “this product is GDPR-compliant” catalogue. Certification is voluntary under GDPR Arts. 42–43.

#### Video / biometrics

- [Συστήματα βιντεοεπιτήρησης](https://www.dpa.gr/enimerwtiko/thematikes_enotites/eisagwgi_videoepitirisi) — still uses **Οδηγία 1/2011**, read together with GDPR and [EDPB Guidelines 3/2019](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-32019-processing-personal-data-through-video_en)
- [FAQ βιντεοεπιτήρηση](https://www.dpa.gr/el/enimerwtiko/thematikes_enotites/eisagwgi_videoepitirisi/faq_videoepitirisi)
- No prior HDPA licence / notification is required anymore; accountability, signage, RoPA, and usually a DPIA are
- Biometrics = Art. 9 special-category data; identification is high-risk

### 3.2 Cybersecurity (NCSA)

#### For all organisations (best-practice handbook)

- [Cybersecurity Handbook (EN)](https://cyber.gov.gr/wp-content/uploads/2025/04/Cybersecurity-Handbook-English-version-1.pdf)

18 control families aligned with ISO 27001 and NIST CSF: governance, CISO, access control, network, web apps, backups, incident response, etc.

#### If you are (or sell to) a NIS2 essential / important entity — binding

- Law **5160/2024** (NIS2 transposition — already in force)
- [NIS2 page](https://cyber.gov.gr/odigia-nis2/)
- [Scope / applicability test](https://cyber.gov.gr/nis2-scope/)
- Register: [nis2register.cyber.gov.gr](https://nis2register.cyber.gov.gr/)
- Binding control set: **ΚΥΑ 1689/2025 — Εθνικό Πλαίσιο Απαιτήσεων Κυβερνοασφάλειας** ([announcement](https://cyber.gov.gr/thespisi-ethnikoy-plaisioy-apaitiseon-kyvernoasfaleias-gia-vasikes-kai-simantikes-ontotites/))
  - **22 requirements**: policies, risk management, asset inventory, access control, supply chain, incident response, backups, training, etc.
- Incident reporting: 24h early warning, 72h detailed report, 1-month final report

This Greek framework is the closest analogue to France’s ANSSI hygiene + future NIS2 measures. Unlike France, Greece **already has a national binding control list**.

---

## 4. EU layer both countries apply

Use these with the national lists; they are the common legal floor:

- GDPR Arts. 5, 25, 28, 32, 33–34, 35
- [EDPB Guidelines 3/2019 — video devices](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-32019-processing-personal-data-through-video_en)
- EDPB Guidelines on DPIA (WP248)
- NIS2 Directive (EU) 2022/2555
- ENISA technical guidance for NIS2 / cybersecurity

---

## 5. Reading for an EyeNet-style vendor

For video analytics, both DPAs treat **anonymous / on-device detection** much more favourably than **identification**. Facial recognition needs a GDPR Art. 9 exception, a DPIA, and usually a specific legal basis. It cannot be “ticked compliant” by citing on-prem deployment.

Practical stack to keep on file:

**France (privacy + cyber)**

1. CNIL 4 steps + TPE/PME checklist
2. CNIL 2024 security guide (25 fiches) + checklist
3. ANSSI 42 hygiene measures + EBIOS RM
4. ANSSI product/service catalogue and SecNumCloud only if selling qualified security or hosting sensitive cloud
5. CNIL caméras augmentées / facial-recognition positions for any vision feature

**Greece (privacy + cyber)**

1. HDPA 10 steps + byDesign toolkit
2. HDPA DPIA list (Decision 65/2018) and completeness criteria
3. HDPA Directive 1/2011 + EDPB 3/2019 for cameras
4. NCSA Cybersecurity Handbook
5. If NIS2-in-scope (customer or EyeNet itself): Law 5160/2024 + KYA 1689/2025 22 requirements + NCSA register

---

## 6. Primary source index

### France

| Resource | URL |
|---|---|
| CNIL first steps | https://www.cnil.fr/fr/passer-laction/rgpd-les-premieres-etapes |
| CNIL TPE/PME checklist | https://www.cnil.fr/sites/cnil/files/atoms/files/check-list_rgpd_pour_les_tpe-pme.pdf |
| CNIL document the compliance | https://www.cnil.fr/fr/documenter-la-conformite |
| CNIL PIA tool | https://www.cnil.fr/en/open-source-pia-software-helps-carry-out-data-protection-impact-assessment |
| CNIL security guide 2024 | https://www.cnil.fr/fr/guide-de-la-securite-des-donnees-personnelles-nouvelle-edition-2024 |
| CNIL security checklist | https://cnil-d10.cnil.fr/sites/cnil/files/2024-03/guide_securite_donnees_personnelles_checklist.pdf |
| CNIL augmented cameras | https://www.cnil.fr/fr/cameras-augmentees-espaces-publics |
| ANSSI hygiene guide | https://messervices.cyber.gouv.fr/guides/guide-dhygiene-informatique |
| EBIOS RM | https://messervices.cyber.gouv.fr/guides/la-methode-ebios-risk-manager-le-guide |
| ANSSI qualified catalogue | https://cyber.gouv.fr/offre-de-service/solutions-certifiees-et-qualifiees/services-de-securite-evalue/decouvrir-les-solutions-certifiees-qualifiees/ |
| SecNumCloud | https://cyber.gouv.fr/enjeux-technologiques/cloud/ |
| ANSSI NIS2 | https://messervices.cyber.gouv.fr/nis2 |
| Cybermalveillance | https://www.cybermalveillance.gouv.fr |

### Greece

| Resource | URL |
|---|---|
| HDPA GDPR guide (10 steps) | https://www.dpa.gr/el/foreis/odigos_gkpd |
| byDesign toolkit | https://www.dpa.gr/el/byDesign_toolkit |
| HDPA DPIA list | https://www.dpa.gr/el/enimerwtiko/prakseisArxis/katalogos-me-ta-eidi-ton-praxeon-epexergasias-poy-ypokeintai-stin |
| DPIA completeness criteria | https://www.dpa.gr/sites/default/files/2020-12/ESSENTIAL_STANDARD_CRITERIA_DPIA_0.pdf |
| Video surveillance | https://www.dpa.gr/enimerwtiko/thematikes_enotites/eisagwgi_videoepitirisi |
| NCSA | https://cyber.gov.gr |
| Cybersecurity Handbook (EN) | https://cyber.gov.gr/wp-content/uploads/2025/04/Cybersecurity-Handbook-English-version-1.pdf |
| NIS2 | https://cyber.gov.gr/odigia-nis2/ |
| NIS2 scope test | https://cyber.gov.gr/nis2-scope/ |
| NIS2 register | https://nis2register.cyber.gov.gr/ |
| National Cybersecurity Requirements Framework (KYA 1689/2025) | https://cyber.gov.gr/thespisi-ethnikoy-plaisioy-apaitiseon-kyvernoasfaleias-gia-vasikes-kai-simantikes-ontotites/ |

### EU

| Resource | URL |
|---|---|
| EDPB Guidelines 3/2019 (video) | https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-32019-processing-personal-data-through-video_en |
