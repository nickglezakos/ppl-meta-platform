# Authority Business Operations Proposal

**Date**: May 28, 2026  
**Status**: Proposed  
**Scope**: Define the real-world operational roles of admin, distributor, reseller, and support across the Eyent software lifecycle  
**Related Documents**: [docs/proposals/authority/authority-policy.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/authority/authority-policy.md), [docs/proposals/authority/admin-console-actions-and-hierarchy-clarification.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/authority/admin-console-actions-and-hierarchy-clarification.md)

---

## Purpose

This proposal defines the business and operational meaning of four production roles in the Eyent software operating model:

- admin
- distributor
- reseller
- support

This is not a proposal about their account permissions inside the authority service.

It is instead a high-level operating model for how those roles participate in the commercial, onboarding, operational, and customer lifecycle of the Eyent platform in real production use.

The goal is to provide a simple shared language for future UX, workflow, automation, and policy prompts.

---

## Core Principle

The four roles should be treated as operational responsibilities in the customer lifecycle, not only as software access levels.

At a high level:

- `admin` owns platform governance, policy, commercial control, and exceptional decision-making
- `distributor` owns regional or channel-scale commercial enablement and operational coordination
- `reseller` owns the direct customer relationship and day-to-day account progression
- `support` owns technical recovery, diagnosis, and service continuity

These roles may collaborate on the same customer account, but they should not be treated as interchangeable.

---

## Role Definitions

### Admin

The admin role acts as the platform authority and governance layer.

Admin is responsible for:

- defining commercial and operational policy
- approving or overseeing exceptional lifecycle actions
- managing top-level channel structure and business rules
- handling escalations that cross reseller or distributor boundaries
- deciding suspension, reinstatement, special approval, or exception outcomes

Admin should operate as the control plane for the business, not the default actor for routine customer work.

### Distributor

The distributor role acts as the scale and coordination layer between platform governance and the field channel.

Distributor is responsible for:

- enabling and supervising reseller performance within a territory, business unit, or commercial segment
- monitoring onboarding quality and operational readiness across multiple reseller relationships
- coordinating larger deployments or structured rollout programs
- identifying systematic risks in adoption, delivery, or account health
- escalating channel or account issues that exceed reseller capacity

Distributor should focus on operational leverage and channel quality, not on acting as direct customer support for every case.

### Reseller

The reseller role acts as the primary customer-facing commercial and onboarding owner.

Reseller is responsible for:

- managing the direct commercial relationship with the customer
- converting opportunity into sale and customer activation
- preparing the customer for onboarding and correct initial usage
- maintaining account momentum after go-live
- coordinating customer communication in both positive and difficult lifecycle moments

Reseller should be understood as the main business owner of the customer relationship.

### Support

The support role acts as the technical service continuity and recovery function.

Support is responsible for:

- diagnosing technical issues
- guiding recovery actions
- protecting operational continuity during incidents
- separating product misuse from product defect or deployment defect
- providing actionable technical findings to the rest of the operating model

Support should not own the commercial relationship, but it must enable the commercial roles to manage that relationship credibly.

---

## Lifecycle View

The role model becomes clearer when described by lifecycle phase.

### 1. Presales

The presales phase is about qualification, fit, solution framing, and commercial readiness.

At a high level:

- `admin` sets the overall offer structure, operating rules, and exception boundaries
- `distributor` aligns regional/channel capacity and identifies which reseller or commercial path should own the opportunity
- `reseller` leads the direct customer conversation, discovery, and fit validation
- `support` contributes only when technical feasibility, integration risk, or deployment complexity must be clarified

The key output of presales is not just a sale opportunity. It is a clear operating path for the account.

### 2. Sales

The sales phase is about commercial closure and commitment.

At a high level:

- `admin` governs pricing policy, strategic exceptions, and unusual approval requirements
- `distributor` manages channel coordination, volume planning, and rollout alignment for larger deals
- `reseller` owns commercial closure with the customer and ensures expectations are realistic
- `support` may validate implementation assumptions where technical risk could undermine the sale

The key output of sales is a customer commitment that is operationally supportable.

### 3. Onboarding

The onboarding phase is where the customer transitions from sold account to activated account.

At a high level:

- `admin` defines the approved lifecycle pattern and handles exceptions or sensitive approvals
- `distributor` monitors onboarding quality across channel partners and intervenes when rollout quality degrades
- `reseller` owns the customer-facing onboarding journey, readiness checks, and progression toward first successful activation
- `support` assists where technical recovery or installation troubleshooting is required

The reseller should normally be the visible business owner of onboarding. Support should be brought in to unblock technical issues, not replace the reseller relationship.

### 4. Operations Events

Operations events include normal business events that occur after onboarding, such as expansions, configuration changes, personnel changes, deployment changes, entitlement changes, renewals, and account-health shifts.

At a high level:

- `admin` governs policy-sensitive changes and cross-account consistency
- `distributor` tracks patterns across multiple reseller-managed customers and intervenes when there is systemic risk
- `reseller` owns customer communication and business follow-through for routine operational changes
- `support` handles technical implications of those changes when they affect service continuity or software behavior

The key principle is that business ownership and technical execution may be separate, but they must remain coordinated.

### 5. Problem Solving

Problem solving includes technical incidents, workflow failures, adoption blockers, and ambiguous account situations.

At a high level:

- `admin` decides policy-level resolutions when a case becomes exceptional or disputed
- `distributor` coordinates multi-party problem solving where the issue affects channel performance or multiple accounts
- `reseller` owns customer-facing accountability and expectation management
- `support` owns diagnosis, evidence gathering, recovery guidance, and technical root-cause clarity

Problem solving should not default to support alone. In production reality, effective resolution usually combines reseller accountability with support diagnosis.

### 6. Customer Success

Customer success is about durable adoption, value realization, and retention.

At a high level:

- `admin` defines the success standards, operating policies, and retention rules for the platform business
- `distributor` monitors health trends across portfolios and pushes channel improvements where needed
- `reseller` owns the ongoing customer relationship, growth opportunities, and account health conversation
- `support` contributes operational insight that helps explain recurring friction or technical value blockers

Customer success should be treated as an operating outcome owned commercially and informed technically.

### 7. Churn Management

Churn management includes renewal risk, inactivity, dissatisfaction, commercial breakdown, and managed offboarding.

At a high level:

- `admin` sets the policy for suspension, recovery, reinstatement, or termination when an account reaches a serious lifecycle decision
- `distributor` helps assess broader channel impact and whether intervention is needed above reseller level
- `reseller` owns the direct retention conversation, account rescue attempts, and transition handling
- `support` clarifies whether technical issues contributed materially to churn risk and what recovery options remain possible

Churn should not be treated only as a sales failure or only as a technical failure. It is usually a combined business and operational outcome.

---

## Problematic Customer Cases

The operating model becomes especially important in difficult customer situations.

### Customer Suspension

When a customer must be suspended because of non-payment, misuse, policy breach, security risk, or operational conflict:

- `admin` should own the governing decision or policy framework
- `distributor` should coordinate when channel-scale or regional consequences exist
- `reseller` should manage the customer-facing communication and attempt structured resolution where appropriate
- `support` should protect service integrity and execute any required technical containment or recovery action

The key rule is that suspension is a business-controlled action with technical consequences, not merely a technical switch.

### Misuse Or Problematic Use Cases

Problematic use may include abuse, repeated policy violations, unsupported usage patterns, or operational behavior that creates risk for the platform or partner network.

At a high level:

- `admin` defines what constitutes unacceptable use and what escalations are allowed
- `distributor` helps evaluate whether the pattern is isolated or systemic across the channel
- `reseller` works directly with the customer to correct behavior or reset expectations
- `support` documents the technical symptoms, impact, and recovery boundaries

The operating model should distinguish clearly between:

- customer education issues
- commercial issues
- technical issues
- policy enforcement issues

### Escalated Service Failures

When a customer experiences repeated service disruption or a high-stakes operational failure:

- `admin` may need to approve exceptions, credits, special handling, or policy deviations
- `distributor` may coordinate a broader remediation approach if multiple accounts are affected
- `reseller` remains responsible for customer trust and relationship continuity
- `support` leads technical triage, remediation, and evidence-based follow-up

These cases should be handled as coordinated operational incidents, not as isolated ticket exchanges.

---

## Proposed Operating Interpretation

For future product and workflow prompts, the roles should be interpreted like this:

- `admin` = business governance and exceptional authority
- `distributor` = channel coordination and scaled operational supervision
- `reseller` = direct customer business owner
- `support` = technical continuity and recovery owner

This interpretation should guide:

- workflow design
- dashboard framing
- escalation rules
- lifecycle messaging
- future automation prompts
- authority UI and proposal language

---

## Recommendation

Future versions should keep this business model high-level and stable.

More detailed prompts, workflows, or UI changes can then refine:

- what each role sees first
- what each role is allowed to trigger
- which lifecycle events require cross-role approval
- how customer-risk states are surfaced operationally
- how the platform separates policy decisions from technical actions

The important foundation is to keep the roles grounded in real production operations, not just in software account types.
