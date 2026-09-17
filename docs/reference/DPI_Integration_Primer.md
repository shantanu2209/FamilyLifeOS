# Technical Knowledge Base: Holistic LifeOS Architecture & DPI Specs

> **Status:** REFERENCE — early technical knowledge base · **Author:** Shantanu Chaudhary (Lead Product Architect) · **Last content change:** 2026-01
> **Canonical copy.** Converted to Markdown on 2026-09-16 from `Technical Knowledge Base.docx` (original kept in `archive/originals/`). Content is unchanged; only formatting was converted.
> **Cited elsewhere as:** Technical Knowledge Base.
> **Note:** Filed as a DPI integration primer: the ONDC/Beckn flow, AA entity chain, ABHA/FHIR flow, Bhashini APIs and the Conflict Object shape are still useful background. Its JSON schemas (§3) are superseded by Data_Model_Schema.md and its security notes (§4) by Master_Context.md §7.

Purpose: This document provides the technical specifications, architectural patterns, and India Stack integration guides for the Holistic LifeOS Gem.

## 1. High-Level Architecture: The "Supervisor-Worker" Model

We use a Multi-Agent Orchestration pattern. We do not use a single LLM for everything.

### The Supervisor (Orchestrator)

- Function: State Machine & Router.
- Responsibility: Maintains the "Global Context" (User ID, Current Budget, Active Goals).
- Logic:
  - Receives user intent ("Plan a trip").
  - Breaks it down into sub-tasks.
  - Delegates to Worker Agents (Logistics Agent, Finance Agent).
  - Synthesizes output.

### The Worker Agents

Each Agent is a specialized LLM instance with specific Tools (APIs).

| Agent Name | Primary Tools | Context Window |
|---|---|---|
| Health Agent | fetch_abha_records(), search_ondc_pharma() | Medical History, Diet Prefs |
| Finance Agent | fetch_aa_data(), execute_bbps_pay(), check_budget() | Bank Balances, Bill Dues |
| Home Ops Agent | search_ondc_services(), update_inventory() | Appliance List, AMC Dates |
| Vault Agent | fetch_digilocker_doc() | Document Metadata |

## 2. India Stack (DPI) Integration Cheat Sheet

### A. ONDC (Open Network for Digital Commerce)

- Role: Hyperlocal Commerce (Groceries, Meds, Services).
- Protocol: Beckn Protocol.
- Flow:
  - search: Agent broadcasts intent (e.g., "item: paracetamol", "location: gurgaon").
  - select: Agent picks the best provider (Price vs. Speed).
  - init: Agent sends order details.
  - confirm: Payment & Finalization.
- Strategy: We act as a Buyer App (BAP) in the ONDC network.

### B. Account Aggregator (AA) framework

- Role: Financial Data Fetching.
- Key Entities: FIP (Financial Information Provider - Banks) -> AA (Consent Manager) -> FIU (Financial Information User - Us).
- Data Types: Savings, Current, Deposits, SIPs, Insurance Policies, GST Returns.
- Consent: We must request explicit consent for specific data types and durations. "One-time fetch" or "Periodic fetch".

### C. ABHA (Ayushman Bharat Health Account)

- Role: Health Records.
- Integration: PHR (Personal Health Record) App.
- Flow:
  - User authenticates via ABHA Number (OTP).
  - App requests access to "Lab Reports" from linked HIPs (Health Info Providers).
  - Data is received in FHIR format (Standard healthcare data format).

### D. Bhashini (National Language Translation Mission)

- Role: Voice Interface.
- APIs:
  - ASR (Automatic Speech Recognition): Audio -> Text.
  - NMT (Neural Machine Translation): Hindi Text -> English Text (for Agent processing).
  - TTS (Text to Speech): English Response -> Hindi Audio.

## 3. Data Schemas (JSON Contracts)

### A. The Family Graph Node

{  
  "user_id": "uuid_v4",  
  "role": "admin | spouse | child | staff",  
  "permissions": ["view_finance", "edit_health", "view_tasks"],  
  "relationships": [  
    { "target_user_id": "uuid_spouse", "type": "spouse" },  
    { "target_user_id": "uuid_driver", "type": "staff" }  
  ],  
  "dpi_links": {  
    "abha_id": "string",  
    "digilocker_uuid": "string"  
  }  
}

### B. The "Conflict" Object (For Orchestration)

When Agents disagree, they generate this object for the Supervisor.
{  
  "conflict_id": "c_102",  
  "source_agent": "FinanceAgent",  
  "target_agent": "LogisticsAgent",  
  "issue": "Budget Exceeded",  
  "details": {  
    "proposed_spend": 200000,  
    "available_limit": 50000,  
    "blocking_reason": "Upcoming Insurance Premium"  
  },  
  "suggested_resolution": "Delay trip by 2 months OR reduce duration to 3 days"  
}

## 4. Security & Privacy Standards

- Zero Knowledge Storage: We do not store raw bank passwords. We only store the Consent Handle from AA.
- Local Encryption: Sensitive health/finance data should be encrypted on the device where possible, or strictly siloed in the cloud with per-user encryption keys.
- RBAC Enforcement: Every API call must pass a check_permission(user_role, resource) middleware.
