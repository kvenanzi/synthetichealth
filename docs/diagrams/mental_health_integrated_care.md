# Mental Health Integrated Care Module

```mermaid
stateDiagram-v2
    [*] --> Intake

    state "intake_visit\nEncounter: Behavioral Health Intake" as Intake
    state "mental_health_conditions\nCondition Onset: MDD & GAD" as Dx
    state "collaborative_care_plan\nCare Plan: Collaborative Care Plan" as CarePlan
    state "baseline_assessments\nObservations: PHQ-9 15-22, GAD-7 12-19" as Baseline
    state "initial_medication\nMedications: Sertraline 50 mg, Hydroxyzine 25 mg PRN" as Meds
    state "follow_up_delay\nDelay: 60 days" as Delay
    state "follow_up_decision\nDecision" as Decision
    state "telehealth_follow_up\nEncounter: Telehealth Visit" as Telehealth
    state "telehealth_assessments\nObservation: PHQ-9 8-14" as TeleAssess
    state "in_person_follow_up\nEncounter: Behavioral Health Follow-up" as InPerson
    state "in_person_assessments\nObservations: PHQ-9 6-12, GAD-7 7-14" as InPersonAssess
    state "crisis_intervention\nEncounter: Urgent Behavioral Health Visit" as Crisis
    state "crisis_procedures\nProcedure: Collaborative Care Management (CPT 99492)" as CrisisProc
    state "safety_plan\nCare Plan: Safety Planning Intervention" as SafetyPlan

    Intake --> Dx
    Dx --> CarePlan
    CarePlan --> Baseline
    Baseline --> Meds
    Meds --> Delay
    Delay --> Decision

    Decision --> Telehealth: 60%
    Decision --> InPerson: 25%
    Decision --> Crisis: 15%

    Telehealth --> TeleAssess
    TeleAssess --> Delay

    InPerson --> InPersonAssess
    InPersonAssess --> Delay

    Crisis --> CrisisProc
    CrisisProc --> SafetyPlan
    SafetyPlan --> Delay
```

**Legend**
- Decision branches reflect module probabilities (`follow_up_decision`).
- Observations capture PHQ-9/GAD-7 trajectories; crisis path adds CPT 99492 and returns to the follow-up loop via the safety plan.
