# Master Product Requirement Document (PRD): Holistic LifeOS

> **Status:** REFERENCE — Master PRD v2.1 (India Stack Integrated) · **Author:** Shantanu Chaudhary (Lead Product Architect) · **Last content change:** 2026-01
> **Canonical copy.** Converted to Markdown on 2026-09-16 from `Holistic_LifeOS_Master_PRD.md.docx` (original kept in `archive/originals/`). Content is unchanged; only formatting was converted.
> **Cited elsewhere as:** Holistic LifeOS Master PRD v2.1.
> **Note:** This is the module-level master PRD. It is not the scenario-driven "PRD_FamilyLifeOS_Core_v2.1" that the tech specs cite, which is not in this repository (AGENTS.md §3.1). Its phasing (§6) is superseded by Master_Context.md §8, which accounts for regulatory approval timelines.

Vision: The Family Operating System (FamilyOS)
Version: 2.1 (India Stack Integrated)
Owner: Director of Product
Date: January 2026

## 1. Product Vision

Holistic LifeOS is not just an app; it is the "Central Nervous System" for the modern family. It uses Agentic AI to bridge the gaps between health, wealth, logistics, and communication, moving the user from "managing tasks" to "governing outcomes."
**Core Differentiator: DPI-Native Agentic Orchestration.**
- Competitors: Build walled gardens (proprietary data).
- LifeOS: Built on the India Stack. The "Health Agent" fetches lab reports via ABHA, the "Shopping Agent" orders meds via ONDC, and the "Finance Agent" pays via UPI.

## 2. Target Audience & Persona

- Primary User (Admin): The "Chief Family Officer" (e.g., Head of Household). Wants control, visibility, and automation.
- Secondary Users:
  - Dependents: Children (School tracking), Elderly Parents (Health tracking via voice).
  - External Stakeholders: Household Help, Driver (Interaction via vernacular voice).

## 3. The Core Platform: "The Family Graph"

This is the foundation upon which all modules sit.

### 3.1 Family Identity & Roles

- Relationship Mapping: Spouse, Kids, Parents, In-Laws, Pets, Service Staff.
- Role-Based Access Control (RBAC): Admin, Spouse (Shared), Child (Limited), Staff (Transactional).

### 3.2 The "Family Dashboard" (Command Center)

- Unified Feed: "Electricity Bill Due (BBPS)", "Dad's BP Low (ABHA)", "Fancy Dress Friday (School)".
- Filters: Person-view vs. Category-view.

### 3.3 The Vernacular Interface (Bhashini Integration)

- Requirement: Voice-First interaction for non-tech-savvy members (Parents/Staff).
- Tech: Integration with Bhashini API for real-time speech-to-text in 10+ Indian languages.
  - Use Case: Driver speaks in Hindi: "Madam, car service due." -> App translates and adds task to "Home Ops" module.

## 4. Module Requirements (The Ecosystem)

### Module 1: Health & Wellness (The Body)

- Profile-Based Needs: Custom plans (Diabetic, Pediatric, Geriatric).
- DPI Integration: ABDM (Ayushman Bharat Digital Mission)
  - ABHA (Health ID): Link family members' ABHA IDs to fetch lab reports and prescriptions automatically.
  - UHI (Unified Health Interface): AI Agent books doctor appointments directly.
- Commerce:
  - ONDC (F&B/Pharma): "Shopping Agent" compares prices for prescriptions across local pharmacies and orders via ONDC.

### Module 2: Financial Command Center (The Wallet)

- DPI Integration: Account Aggregator (AA)
  - Real-Time Visibility: Fetches consolidated view of Banks, SIPs, and Insurance without screen-scraping.
- DPI Integration: ULI (Unified Lending Interface) / OCEN
  - Credit Agent: "Vacation planning? Based on your cash flow, you qualify for a pre-approved travel loan via ULI."
- Payments:
  - BBPS: Utility Bills, School Fees, FASTag.
  - P2P Payroll: Recurring UPI Autopay for Maids/Drivers.

### Module 3: Home Operations (The House)

- Smart Inventory: Predictive replenishment.
- Commerce: ONDC (Services)
  - Service Agent: Instead of just "Urban Company," the agent broadcasts a service request (e.g., "AC Repair") on ONDC to find the best-rated local technician.

### Module 4: Family Logistics (The Movement)

- Vacation Planner: Integrated with Finance (Budget) and School (Dates).
- Travel:
  - DigiYatra: "Travel Agent" retrieves and shares DigiYatra credentials before flights.
- Education (DIKSHA / DigiLocker):
  - Fetch verified Marksheets and School Certificates directly from DigiLocker.
  - Access curriculum resources via DIKSHA for homework help agents.

### Module 5: The Secure Vault (The Safe)

- DPI Integration: DigiLocker
  - Source of Truth: The vault doesn't just store files; it syncs with DigiLocker.
  - Voice Retrieval: "Hey LifeOS, show my Driving License" -> Fetches verified copy.

### Module 6: Communication & Info Hub (The Pulse)

- Family Chat: Private messaging.
- The "Daily Brief": Personalized news + Brain Gym (Sudoku/Crosswords).

### Module 7: Elder Care Protocol (The Care)

- Vitals Tracking: Log BP/Sugar.
- Emergency: One-touch SOS.
- Integration: ABHA records shared with emergency contacts instantly.

## 5. Agentic Capabilities (The "Why AI?")

The secret sauce is how Agents orchestrate DPIs.
- The "Medical Emergency" Orchestration:
  - Trigger: Elderly parent's smartwatch detects fall/arrhythmia.
  - Action: Health Agent pulls history via ABHA. Logistics Agent books ambulance via ONDC/Uber. Finance Agent pre-authorizes payment via UPI. Comms Agent alerts family.
- The "Grocery Inflation" Arbitrage:
  - Trigger: Weekly grocery list generated.
  - Action: Shopping Agent queries ONDC to compare "Blinkit" vs "Local Kirana" prices. Splits the order to save ₹500.

## 6. Phased Execution Roadmap

- Phase 1 (The Core + Health): Family Graph + Module 1 (Diet Agent).
- Phase 2 (The Data Layer): Integrate Account Aggregator (Finance) and DigiLocker (Vault).
- Phase 3 (The Commerce Layer): Integrate ONDC (Shopping/Meds) and BBPS (Bills).
- Phase 4 (The Voice Layer): Integrate Bhashini for vernacular support.

## 7. Success Metrics

- Orchestration Rate: % of tasks involving >1 module.
- DPI Success Rate: % of successful fetches (ABHA/AA/DigiLocker).
- Time Saved: Estimated hours saved per month via ONDC/BBPS automation.
