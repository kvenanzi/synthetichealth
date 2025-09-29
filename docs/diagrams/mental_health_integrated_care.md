# Mental Health Integrated Care Module

```mermaid
stateDiagram-v2
    [*] --> Intake: start

    state "Intake Visit\n(Encounter)" as Intake
    state "Diagnose Depression & Anxiety\n(Condition Onset)" as Dx
    state "Collaborative Care Plan" as CarePlan
    state "Baseline Assessments\n(PHQ-9, GAD-7)" as Baseline
    state "Initial Medication\n(Sertraline, Hydroxyzine)" as Meds
    state "60-Day Delay" as Delay
    state "Follow-up Decision" as Decision
    state "Telehealth Follow-up" as Telehealth
    state "Telehealth Assessments" as TeleAssess
    state "In-person Follow-up" as InPerson
    state "In-person Assessments" as InPersonAssess
    state "Crisis Intervention" as Crisis
    state "Collaborative Care CPT 99492" as CrisisProc
    state "Safety Plan Refresh" as SafetyPlan

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
