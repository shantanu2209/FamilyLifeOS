# PRD: [Module/Feature Name]

> **Status:** TEMPLATE · **Author:** Shantanu Chaudhary (Lead Product Architect) · **Last content change:** 2026-01
> **Canonical copy.** Converted to Markdown on 2026-09-16 from `LifeOS Deep-Dive PRD Template.docx` (original kept in `archive/originals/`). Content is unchanged; only formatting was converted.
> **Cited elsewhere as:** LifeOS Deep-Dive PRD Template.
> **Note:** Use for module or feature PRDs (the P1 module PRDs the Module Registry defers to). Copy, rename, fill in. Two images in the original (Figma sketches placeholder) were not carried over.

Status: Backlog / In-Progress / In-Review / Shipped
Author: [Name]
Primary Agent: [e.g., FinanceAgent, HealthAgent, Supervisor]
Engineering Lead: [Name]
Design Lead: [Name]
Approvers: [Names]

## 0. Document Governance

Track the evolution of this agentic feature.

| Version | Date | Description of Change | Author |
|---|---|---|---|
| v0.1 | [Date] | Initial Draft | [Name] |

## 1. The One-Pager (Executive Summary)

- Overview: (Briefly state what this project is about and its importance).
- The Problem (The Friction): (Explain the current manual household nightmare and related customer pain points).
- Objectives (The Outcome): (What does success look like? What are the broad brush goals?).
- Constraints: (Roadblocks, realities, and dependencies—time, money, or engineering limits).

## 2. Personas & The Family Graph (RBAC)

Who interacts with this feature and what is their permission level?

### Target Personas

- Key Persona: [e.g., The Decision Maker / Admin]
- Secondary Personas: [e.g., Elderly Parent, Household Staff, Child]

### Access Control Matrix

| Role | Access Level | LifeOS Use Case |
|---|---|---|
| Admin (Head of House) | Full Control | Approval of high-value transactions/records. |
| Spouse | Co-Manager | Full visibility into shared logs. |
| Elderly Parent | View/Voice Only | Receives simplified summaries via Bhashini. |
| Staff (Driver/Maid) | Restricted | "Task-only" access (e.g., attendance/salary). |

## 3. User Scenarios / Use Cases

Describe the 'Golden Path' in a narrative format.
- Scenario 1: (e.g., Admin setting up automated salary for the Driver).
- Scenario 2: (e.g., Agent detecting a budget conflict and proposing a resolution).

## 4. Functional Requirements (The "Agentic" Loop)

This is the 'Features In' section, expanded for AI autonomy.
- Trigger: (What starts the process? Scheduled date, low balance, voice command).
- Information Gathering: (Which DPI or local data does the agent fetch?).
- Analysis Logic (The 'Brain'): (How does the agent think? e.g., "If , then suggest ").
- Execution/Fulfillment: (Does it use ONDC? UPI? Push notification?).

### Features In (Prioritized)

- [Feature Name] [M]: (Description and why it's a Minimum Viable Experience).
- [Feature Name]: (Description).

### Features Out

- (What have you explicitly decided NOT to do and why?).

## 5. India Stack (DPI) Touchpoints

How we leverage the national rails.
- Identity: (Aadhaar/DigiLocker requirements).
- Data: (Account Aggregator / ABHA / DIKSHA integration details).
- Payments: (UPI intent / BBPS autopay).
- Commerce: (Beckn/ONDC search parameters).

## 6. Conflict Resolution Matrix

Defining the logic for when Agents or Family Members disagree.

| Conflict Scenario | Resolution Logic |
|---|---|
| Budget Overrun | Finance Agent flags for Admin approval. |
| Privacy Violation | Vault Agent blocks access and logs the event. |
| Schedule Clash | Logistics Agent proposes 3 alternative slots. |

## 7. Design & Generative UI

Focus on 'States' rather than static screens.
- Voice Flow: (Bhashini-optimized prompts and vernacular logic).
- Dashboard Widget: (Description of the 'Live Card' on the home screen).
- Critical Alerts: (Visual/Audio behavior for SOS or urgent notifications).
- Early Sketches: (Link to Figma/Miro if available).

## 8. Technical Considerations & Success Metrics

### Technical Approach

- (Link to engineering tech spec document).
- (Known API dependencies or rate limits).

### Success Metrics (The Autonomy Score)

- Completion Rate: % of tasks completed without user "correction."
- DPI Reliability: % of successful data fetches from India Stack.
- Family NPS: Household satisfaction via vernacular feedback.

## 9. GTM & Operations

- Messaging: (How will Marketing describe this to existing and new users?).
- Launch Plan: (Phased rollout? Beta group?).
- Timeline & Phasing:
  - Phase 1: (Date - Feature Set)
  - Phase 2: (Date - Feature Set)

## 10. Open Issues & Q&A

### Open Issues

- (Unresolved factors/risks).

### Q&A

| Asked By | Question | Answer |
|---|---|---|
| [Name] | [Question] | [Answer] |

## 11. PRD Checklist

- [ ] Title & Author defined.
- [ ] Executive One-Pager finalized.
- [ ] Family RBAC permissions mapped.
- [ ] Agentic Loop logic defined.
- [ ] DPI (India Stack) points identified.
- [ ] Conflict Resolution scenarios handled.
- [ ] GTM Approach outlined.
- [ ] Success Metrics (Autonomy Score) set.
