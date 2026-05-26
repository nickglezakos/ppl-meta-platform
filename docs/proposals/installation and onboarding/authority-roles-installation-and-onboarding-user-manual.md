# Authority Roles Installation And Onboarding User Manual

**Date**: May 20, 2026  
**Status**: Draft  
**Audience**: Platform administrators, distributors, resellers, and owners  
**Related Documents**: [docs/proposals/installation and onboarding/platform-settings-authority-application-key-onboarding-contract.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/platform-settings-authority-application-key-onboarding-contract.md), [docs/proposals/installation and onboarding/real-installation-uuid-and-application-key-onboarding-flow.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/real-installation-uuid-and-application-key-onboarding-flow.md), [autonomous/ppl-meta-authority/README.md](/Users/nickgklezakos/Documents/ppl-meta-code/autonomous/ppl-meta-authority/README.md)

---

## Purpose

This manual explains, in non-technical language, how the authority service supports the commercial and onboarding journey for all main roles:

- platform administrator
- distributor
- reseller
- owner

It describes:

- how distributor accounts are created
- how reseller accounts are created
- how software licences are issued for owners
- how owners receive their software licence details
- how owners download the platform images or installers
- how the first owner user completes onboarding for the first time

This document is written for operational use, not for API or engineering implementation work.

---

## Core Idea

The authority service is the control point for onboarding and licence approval.

In practical terms:

- a software licence is issued for an owner
- that software licence becomes the authority application key
- the owner uses that same key during first-time platform setup
- the first owner user is allowed in only when authority approves the key, owner email, and installation identity together

This keeps licensing, activation, and first-user onboarding connected in one flow.

---

## Role Overview

### Platform Administrator

The platform administrator manages the authority system at the top level.

This role is responsible for:

- creating or inviting distributors
- inviting resellers directly when needed
- inviting owners directly when needed
- reviewing licences and onboarding records
- correcting commercial or onboarding mistakes
- supporting escalations when a distributor or reseller cannot complete a task

### Distributor

The distributor manages a commercial region, channel, or portfolio of reseller relationships.

This role is responsible for:

- creating or inviting reseller accounts inside the distributor scope
- overseeing the resellers that belong to that distributor
- monitoring owner onboarding progress across that distributor scope
- supporting resellers when licence issuance or onboarding questions arise

### Reseller

The reseller works directly with the owner customer.

This role is responsible for:

- creating or inviting owner users
- issuing the software licence for the owner
- sharing the onboarding instructions with the owner
- helping the owner complete first-time setup
- confirming that the owner has successfully activated the installation

### Owner

The owner is the customer operating the platform installation.

This role is responsible for:

- receiving the software licence details
- obtaining the platform image, installer, or download package
- entering the licence information during setup
- creating the first owner user account
- completing the first successful activation of the installation

---

## End-To-End Business Flow

The normal commercial and onboarding flow is:

1. the platform administrator creates or invites a distributor
2. the distributor creates or invites a reseller
3. the reseller prepares the owner account and software licence
4. the owner receives the software licence and platform download instructions
5. the owner installs the platform image or package
6. the owner enters the application key and installation details during setup
7. the owner creates the first owner user
8. the authority service approves the onboarding request
9. the installation becomes active for that owner

Depending on the commercial scenario, the administrator may also skip levels and work directly with a reseller or owner.

---

## Part 1: Administrator Guide

### When The Administrator Acts

The administrator usually acts at the start of a new business relationship or when something needs correction.

Examples:

- a new distributor joins the program
- a distributor needs its first reseller added
- a reseller cannot be created through the normal chain
- an owner licence needs correction
- an onboarding issue needs escalation

### Administrator Workflow

1. Sign in to the authority administration interface.
2. Open the user and invitation management area.
3. Create or invite the distributor.
4. Confirm that the distributor invitation has been accepted.
5. Review the distributor scope and make sure it is attached correctly.
6. If needed, create or invite reseller or owner users directly.
7. Review entitlements and installation records when onboarding support is needed.

### What The Administrator Should Provide To A New Distributor

The administrator should provide:

- the distributor invitation or activation instructions
- a short explanation of the distributor role
- the expected next step, which is usually creating or inviting resellers
- support contact details for escalation

### Administrator Checklist

Before handing off to a distributor, confirm:

- the distributor user exists or the invitation has been sent
- the distributor can sign in
- the distributor understands who they are allowed to create next
- any initial reseller plan or scope has been agreed

---

## Part 2: Distributor Guide

### Distributor Goal

The distributor’s main goal is to establish and support reseller relationships.

The distributor does not usually perform the owner’s first-time installation directly, but the distributor should understand the full process in order to guide resellers well.

### Distributor Workflow

1. Sign in to the authority interface.
2. Open the reseller management or invitation area.
3. Create or invite the reseller user.
4. Confirm that the reseller has accepted the invitation.
5. Review which reseller accounts belong to the distributor.
6. Follow up on any reseller that has not completed setup.
7. Support resellers when owner onboarding questions appear.

### What The Distributor Should Provide To A Reseller

The distributor should provide:

- the reseller invitation or sign-in instructions
- the reseller’s commercial scope or portfolio rules
- guidance on how licences should be issued to owners
- guidance on how owners should receive onboarding instructions
- escalation paths for problems the reseller cannot solve alone

### Distributor Checklist

Before handing off to a reseller, confirm:

- the reseller exists or the invitation has been sent
- the reseller can sign in
- the reseller understands how to prepare an owner onboarding package
- the reseller knows how to request support if licensing or activation fails

---

## Part 3: Reseller Guide

### Reseller Goal

The reseller is the key operational role in the commercial onboarding process.

The reseller prepares the owner’s access path and software licence so the owner can activate the platform for the first time.

### Reseller Workflow

1. Sign in to the authority interface.
2. Create or invite the owner user.
3. Create the owner’s software licence record.
4. Confirm the owner email attached to the licence is correct.
5. Share the onboarding package with the owner.
6. Support the owner during first-time setup.
7. Confirm that the owner has completed activation successfully.

### How The Reseller Creates The Owner

The reseller should:

1. open the owner invitation or owner user area
2. enter the owner’s email address carefully
3. send the invitation or create the owner record
4. verify that the owner email matches the intended person responsible for the installation

This email matters because the authority service uses it during first-user approval.

### How The Reseller Issues The Software Licence

The reseller should:

1. open the licence or installation entitlement area
2. create a new licence for the owner
3. attach the correct owner email
4. make sure the licence is active and enabled
5. record any tenant or customer name that helps identify the installation
6. save the record and capture the generated application key or licence number

Important rule:

- the software licence number shared with the owner is the same onboarding key later used during activation

### What The Reseller Sends To The Owner

The owner onboarding package should include:

- the software licence number or application key
- the owner’s approved email address
- the platform image, installer, or download instructions
- the first-time setup instructions
- support contact details if activation fails

### Download Placeholder Section

The exact image or installer distribution flow is not yet finalized.

Placeholder text to replace later:

- `[Placeholder: owner download portal URL]`
- `[Placeholder: Windows installer download instructions]`
- `[Placeholder: Docker image pull instructions]`
- `[Placeholder: appliance image download instructions]`
- `[Placeholder: checksum or integrity verification instructions]`

Until those are finalized, the reseller should send the owner the approved distribution package through the agreed commercial channel.

### Reseller Checklist

Before sending the package to the owner, confirm:

- the owner email is correct
- the licence is active
- the software licence or application key has been captured correctly
- the owner has received the package
- the owner understands who to contact if first activation fails

---

## Part 4: Owner Guide

### Owner Goal

The owner’s goal is to install the platform and activate it for the first time using the issued software licence.

### What The Owner Receives

The owner should receive:

- the software licence number or application key
- the approved owner email address
- the platform image, installer, or package
- the setup instructions
- the contact point for reseller or support help

### Owner First-Time Setup Workflow

1. Download the platform image or installer package.
2. Install or start the platform.
3. Open the settings or onboarding screen.
4. Enter the application key exactly as provided.
5. Confirm or keep the installation UUID shown by the platform.
6. Save the settings.
7. Create the first owner user account.
8. Use the same approved owner email address that was linked to the licence.
9. Complete onboarding.
10. Wait for the platform to contact authority and confirm activation.

If the software licence, owner email, and installation identity match the approved authority record, onboarding should complete successfully.

### What The Owner Should Not Change Lightly

The owner should avoid changing these values casually after setup:

- the application key
- the installation UUID
- the approved owner email used during first activation

Those values are part of the authority approval record.

### Download Placeholder Section For Owners

The final download experience is still pending.

Placeholder text to replace later:

- `[Placeholder: where owners sign in to download installers]`
- `[Placeholder: how owners choose the correct image for their environment]`
- `[Placeholder: hardware-specific installation image options]`
- `[Placeholder: version selection guidance]`
- `[Placeholder: troubleshooting guide for failed downloads]`

### Owner Checklist

Before starting first-time onboarding, confirm:

- you have the correct application key
- you know which email address was approved for your licence
- you have the right installer or platform image
- you know who to contact if activation is rejected

---

## First-Time Owner User Onboarding Explained Simply

The first owner user is the moment when the installation becomes tied to the commercial approval.

In simple terms, the platform checks three things together:

- the software licence or application key
- the owner email
- the installation identity

If those three match what authority expects, the first owner user is approved.

If they do not match, onboarding is refused until the mismatch is corrected.

This protects the installation from being activated by the wrong person or with the wrong licence.

---

## Common Failure Scenarios

### The Owner Uses The Wrong Email Address

Result:

- authority rejects first-time activation

What to do:

- confirm the owner is using the same email address that the reseller linked to the licence

### The Application Key Was Copied Incorrectly

Result:

- authority rejects activation

What to do:

- re-check the exact software licence number or application key

### The Licence Is Not Yet Active

Result:

- activation fails even though the owner has the package

What to do:

- reseller or administrator reviews the licence status and enables it if appropriate

### The Installation Was Already Bound Elsewhere

Result:

- authority refuses the new binding attempt

What to do:

- escalate to reseller or administrator to review the previous activation record

### The Owner Does Not Have The Correct Download Package

Result:

- installation cannot start or the wrong environment is used

What to do:

- resend the approved installer or image package
- replace the placeholder download instructions with the final product delivery steps when available

---

## Role Handover Summary

### Administrator To Distributor

The administrator hands over:

- access to distributor scope
- rules for reseller management
- escalation path

### Distributor To Reseller

The distributor hands over:

- reseller access
- reseller scope
- commercial operating guidance

### Reseller To Owner

The reseller hands over:

- owner access path
- software licence or application key
- platform image or installer package
- first-time onboarding instructions

### Owner To Platform

The owner supplies during onboarding:

- the approved owner email
- the application key
- the installation identity used by the platform

---

## Recommended Operational Practice

To keep onboarding clean and supportable:

- administrators should keep distributor and reseller scopes well organized
- distributors should monitor reseller readiness, not just invitations sent
- resellers should never send an owner package before checking the owner email and licence status carefully
- owners should complete first-time onboarding with the exact approved email and application key they received
- placeholder download instructions should be replaced with finalized distribution steps as soon as the packaging flow is ready

---

## Final Summary

This user manual defines a simple operating model:

- administrators create the commercial channel structure
- distributors create and support resellers
- resellers prepare owner access and issue the software licence
- owners use that licence to install and activate the platform for the first time

The central rule remains the same throughout:

- the software licence issued to the owner is the same onboarding key used to activate the installation

That keeps commercial control, platform activation, and first-user onboarding aligned in one understandable user journey.
