# General Principles and Ruling Thresholds

### 6.1 Monetary Thresholds

| Dispute Value | Ruling Path | Agent Confidence Requirement |
|---|---|---|
| Under $10 | AI agent ruling is **final** | Any confidence level |
| $10 – $50 | AI agent ruling with **80%+ confidence** | If confidence < 80%, escalate to human review |
| Above $50 | **Always human review** | N/A — AI agent prepares case file only |

### 6.2 Category Thresholds

| Dispute Category | Ruling Path |
|---|---|
| Safety incident | **Always human review** (see Section 5) |
| Fare dispute < $10 | AI agent ruling is final |
| Fare dispute $10 – $50 | AI agent ruling if confidence ≥ 80%, else escalate |
| Fare dispute > $50 | Always human review |
| Route deviation | AI agent ruling if confidence ≥ 80% and deviation ≤ 2km, else escalate |
| Property damage (cleaning ≤ $50) | AI agent ruling if photo evidence is verifiable |
| Property damage (repair > $50) | Always human review |
| No-show / cancellation | AI agent ruling is final (fee is fixed at $5.00) |

### 6.3 Confidence Calibration

- Agent confidence is calculated based on: evidence completeness, policy clarity, precedent alignment, and party credibility scores.
- If any party has a fraud flag ≥ 1, the confidence threshold is raised to 95% regardless of dispute value.

---

## Appendix A: Glossary

| Term | Definition |
|---|---|
| **Upfront Quote** | The fare estimate shown to the rider at the time of booking, binding at the surge multiplier in effect at that moment |
| **Actual Fare** | The final fare charged after trip completion, calculated using actual distance, actual time, and the surge multiplier in effect at trip start |
| **Surge Differential** | The difference between the actual fare and the upfront quote, attributable solely to a change in surge multiplier |
| **Surge-Exempt** | Fare components that are not multiplied by the surge multiplier (e.g., booking fee) |
| **No-Show** | A cancellation initiated by the driver after the free wait period because the rider did not appear at the pickup location |
| **AI Agent Ruling** | A dispute resolution decision issued by the RydeResolve AI system without human intervention |
| **Human Review** | A dispute resolution decision requiring human reviewer involvement |

---

## Appendix B: Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2025-06-01 | Initial policy |
| 2.0 | 2025-11-15 | Added surge pricing notification requirements; introduced AI agent ruling thresholds |
| 2.1 | 2026-01-01 | Added precedent rulings framework; expanded property damage evidence requirements; added interim safety measures |

---

*This document is a reference for the RydeResolve multi-agent dispute resolution system. All AI agents must cite the applicable policy section in their ruling rationale.*
