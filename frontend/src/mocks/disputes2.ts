import type { DisputeSpec } from './types'

/* ============================================================
 * Disputes #7–#12
 * ============================================================
 * #7:  property_damage, escalated (driver admits)
 * #8:  safety_incident, escalated
 * #9:  safety_incident, escalated (driver admits, LLM degraded)
 * #10: no_show, open (in progress)
 * #11: route_deviation, open (in progress)
 * #12: route_deviation, full_refund
 */

function ts(day: number, h: number, m: number): string {
  return new Date(2026, 9, day, h, m, 0).toISOString()
}

export const DISPUTES_7_12: DisputeSpec[] = [
  /* ---- #7: property damage, escalated (driver admits) ---- */
  {
    id: 7, trip_id: 7, filed_by: 107,
    category: 'property_damage',
    claim_text: 'Driver spilled coffee on my laptop bag and ruined it.',
    status: 'needs_human_review', priority: 'high',
    created_at: ts(11, 15, 30),
    outcome: 'partial_refund', refund_amount: 21.00, llm_degraded: false,
    rider_opening: {
      sender: 'RiderAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver spilled coffee on the rider\'s laptop bag, causing damage.',
          argument_summary: 'Chat analysis shows the driver admitted to spilling coffee on the rider\'s laptop bag. The driver said "I am sorry about that. The cup slipped." This is a clear admission of fault. Policy section safety_incident#5 covers property damage during a trip.',
          claims: [
            { text: 'The driver admitted to spilling coffee on the rider\'s laptop bag.', evidence_ids: ['chat_analysis:7'], policy_section_ids: ['safety_incident#5'] },
            { text: 'The rider requested compensation immediately.', evidence_ids: ['chat_analysis:7'], policy_section_ids: ['general_principles#4'] },
          ],
          requested_outcome: 'Full compensation for the damaged laptop bag.',
          weaknesses: ['The exact value of the laptop bag is not established.'],
        },
        round: 'opening',
      },
    },
    driver_opening: {
      sender: 'DriverAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver acknowledges the spill but disputes the extent of damage.',
          argument_summary: 'The driver admits a coffee cup slipped but believes the damage to the laptop bag is overstated. The driver is willing to offer a partial compensation but not the full replacement value.',
          claims: [
            { text: 'The spill was accidental and minor.', evidence_ids: ['chat_analysis:7'], policy_section_ids: ['general_principles#4'] },
          ],
          requested_outcome: 'Partial compensation only.',
          weaknesses: ['The driver admitted fault in the chat log.'],
        },
        round: 'opening',
      },
    },
    escalation: {
      sender: 'Judge', recipient: 'HumanReviewer', message_type: 'escalation',
      content: {
        dispute: '#7 (property_damage): Driver spilled coffee on my laptop bag and ruined it.',
        rider_brief: 'The rider reports coffee was spilled on their laptop bag. The driver admitted fault in the chat log.',
        driver_brief: 'The driver acknowledges the spill but disputes the extent of the damage.',
        key_evidence_ids: ['chat_analysis:7'],
        ruling: 'partial_refund — refund $21.00 (confidence 0.72)',
        escalation_reason: 'safety_incident',
        recommended_action: 'Review the chat admission and assess the appropriate compensation amount for the laptop bag damage.',
      },
    },
    ruling: {
      id: 7, outcome: 'partial_refund', refund_amount: 21.00,
      confidence: 0.72,
      reasoning: 'The chat log contains a clear admission from the driver: "I am sorry about that. The cup slipped." This supports the rider\'s claim that the driver caused the damage. However, the exact value of the laptop bag is not established, so a full refund cannot be determined automatically. A provisional partial refund of $21.00 (50% of the trip fare) has been issued pending human review.',
      rule_outcome: {
        rule: { outcome: 'partial_refund', refund_amount: 21.0, matched_rule_ids: [] },
        llm: { outcome: 'partial_refund', refund_amount: 21.0 },
        disagreement: false,
        deciding_evidence_ids: ['chat_analysis:7'],
        deciding_policy_sections: ['safety_incident#5'],
        rejected_claims: [],
        rider_explanation: 'The driver admitted to the spill in the chat log. A partial refund has been issued while a human reviewer assesses the full compensation.',
        driver_explanation: 'You acknowledged the spill. A human reviewer will determine the final compensation amount.',
        tone: 'empathetic',
        confidence_components: { agreement: 1.0, evidence_strength: 0.65, citation_validity: 0.8, history_risk: 0.08, fraud_penalty: 0.0 },
      },
      evidence_ids: ['chat_analysis:7', 'history_profile:7'],
      escalated: true,
      human_review_summary: {
        dispute: '#7 (property_damage): Driver spilled coffee on my laptop bag and ruined it.',
        rider_brief: 'The rider reports coffee was spilled on their laptop bag. The driver admitted fault in the chat log.',
        driver_brief: 'The driver acknowledges the spill but disputes the extent of the damage.',
        key_evidence_ids: ['chat_analysis:7'],
        ruling: 'partial_refund — refund $21.00 (confidence 0.72)',
        escalation_reason: 'safety_incident',
        recommended_action: 'Review the chat admission and assess the appropriate compensation amount for the laptop bag damage.',
      },
      llm_degraded: false,
      created_at: ts(11, 15, 35),
    },
  },

  /* ---- #8: safety incident, escalated ---- */
  {
    id: 8, trip_id: 8, filed_by: 108,
    category: 'safety_incident',
    claim_text: 'Driver was speeding through a school zone. I felt very unsafe.',
    status: 'needs_human_review', priority: 'high',
    created_at: ts(12, 9, 0),
    outcome: 'full_refund', refund_amount: 35.00, llm_degraded: false,
    rider_opening: {
      sender: 'RiderAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The rider experienced unsafe driving behavior during the trip.',
          argument_summary: 'The rider reports the driver was speeding through a school zone. Chat analysis shows the rider raised the safety concern during the trip and the driver denied it. Safety incidents are automatically escalated to human review per safety_incident#5. The rider requests a full refund due to the safety violation.',
          claims: [
            { text: 'The driver was speeding through a school zone.', evidence_ids: ['chat_analysis:8'], policy_section_ids: ['safety_incident#5'] },
            { text: 'The rider expressed safety concerns during the trip.', evidence_ids: ['chat_analysis:8'], policy_section_ids: ['general_principles#4'] },
          ],
          requested_outcome: 'Full refund and driver safety review.',
          weaknesses: ['There is no GPS speed data confirming the speeding. The claim is based on the rider\'s perception.'],
        },
        round: 'opening',
      },
    },
    driver_opening: {
      sender: 'DriverAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver was driving safely and within the speed limit.',
          argument_summary: 'The driver denies speeding and states they were driving within the speed limit at all times. The rider\'s perception of speeding may have been influenced by the road conditions. No GPS speed violation was recorded.',
          claims: [
            { text: 'The driver was driving within the speed limit.', evidence_ids: ['chat_analysis:8'], policy_section_ids: ['general_principles#4'] },
          ],
          requested_outcome: 'No refund or action needed.',
          weaknesses: ['The rider raised the concern during the trip, not after.'],
        },
        round: 'opening',
      },
    },
    escalation: {
      sender: 'Judge', recipient: 'HumanReviewer', message_type: 'escalation',
      content: {
        dispute: '#8 (safety_incident): Driver was speeding through a school zone. I felt very unsafe.',
        rider_brief: 'The rider reports speeding through a school zone and raised the concern during the trip. No GPS speed data confirms the violation.',
        driver_brief: 'The driver denies speeding and claims they were within the speed limit.',
        key_evidence_ids: ['chat_analysis:8'],
        ruling: 'full_refund — refund $35.00 (confidence 0.58)',
        escalation_reason: 'safety_incident',
        recommended_action: 'Investigate the driver\'s speed history and GPS data for this trip. Determine if a safety review is warranted.',
      },
    },
    ruling: {
      id: 8, outcome: 'full_refund', refund_amount: 35.00,
      confidence: 0.58,
      reasoning: 'The rider reported a serious safety concern (speeding through a school zone) during the trip itself. While GPS speed data does not confirm a violation, the rider\'s in-trip report is significant. Safety incidents are automatically escalated per safety_incident#5. A provisional full refund has been issued pending human investigation.',
      rule_outcome: {
        rule: { outcome: 'full_refund', refund_amount: 35.0, matched_rule_ids: [] },
        llm: { outcome: 'full_refund', refund_amount: 35.0 },
        disagreement: false,
        deciding_evidence_ids: ['chat_analysis:8'],
        deciding_policy_sections: ['safety_incident#5'],
        rejected_claims: [],
        rider_explanation: 'Your safety concern was reported during the trip. A full refund has been provisionally issued and a human reviewer will investigate.',
        driver_explanation: 'A safety concern was raised. A human reviewer will investigate the incident.',
        tone: 'empathetic',
        confidence_components: { agreement: 1.0, evidence_strength: 0.45, citation_validity: 0.8, history_risk: 0.20, fraud_penalty: 0.0 },
      },
      evidence_ids: ['chat_analysis:8', 'history_profile:8'],
      escalated: true,
      human_review_summary: {
        dispute: '#8 (safety_incident): Driver was speeding through a school zone. I felt very unsafe.',
        rider_brief: 'The rider reports speeding through a school zone and raised the concern during the trip. No GPS speed data confirms the violation.',
        driver_brief: 'The driver denies speeding and claims they were within the speed limit.',
        key_evidence_ids: ['chat_analysis:8'],
        ruling: 'full_refund — refund $35.00 (confidence 0.58)',
        escalation_reason: 'safety_incident',
        recommended_action: 'Investigate the driver\'s speed history and GPS data for this trip. Determine if a safety review is warranted.',
      },
      llm_degraded: false,
      created_at: ts(12, 9, 5),
    },
  },

  /* ---- #9: safety incident, escalated, LLM degraded ---- */
  {
    id: 9, trip_id: 9, filed_by: 109,
    category: 'safety_incident',
    claim_text: 'Driver ran a red light. We could have been hit.',
    status: 'needs_human_review', priority: 'high',
    created_at: ts(13, 11, 0),
    outcome: 'full_refund', refund_amount: 27.50, llm_degraded: true,
    rider_opening: {
      sender: 'RiderAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver ran a red light, endangering the rider.',
          argument_summary: 'Chat analysis shows the driver admitted to running a red light: "I know, I am sorry. I misjudged the timing." This is a clear admission of a serious safety violation. The rider expressed fear during the trip. Policy section safety_incident#5 mandates escalation for all safety incidents.',
          claims: [
            { text: 'The driver admitted to running a red light.', evidence_ids: ['chat_analysis:9'], policy_section_ids: ['safety_incident#5'] },
            { text: 'The rider expressed fear for their safety during the trip.', evidence_ids: ['chat_analysis:9'], policy_section_ids: ['general_principles#4'] },
          ],
          requested_outcome: 'Full refund and driver suspension pending review.',
          weaknesses: [],
        },
        round: 'opening',
      },
    },
    driver_opening: {
      sender: 'DriverAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver acknowledges the mistake and apologizes.',
          argument_summary: 'The driver admitted to misjudging the traffic light timing and apologized. The driver accepts responsibility for the error. The driver requests understanding given their clean record.',
          claims: [
            { text: 'The driver misjudged the traffic light timing.', evidence_ids: ['chat_analysis:9'], policy_section_ids: ['general_principles#4'] },
          ],
          requested_outcome: 'Leniency given the clean driving record.',
          weaknesses: ['The driver admitted to running a red light.'],
        },
        round: 'opening',
      },
    },
    escalation: {
      sender: 'Judge', recipient: 'HumanReviewer', message_type: 'escalation',
      content: {
        dispute: '#9 (safety_incident): Driver ran a red light. We could have been hit.',
        rider_brief: 'The rider reports the driver ran a red light. The driver admitted fault in the chat log.',
        driver_brief: 'The driver acknowledges the mistake and apologized.',
        key_evidence_ids: ['chat_analysis:9'],
        ruling: 'full_refund — refund $27.50 (confidence 0.68)',
        escalation_reason: 'safety_incident',
        recommended_action: 'The driver admitted to running a red light. Review the driver\'s safety record and determine if suspension is warranted.',
      },
    },
    ruling: {
      id: 9, outcome: 'full_refund', refund_amount: 27.50,
      confidence: 0.68,
      reasoning: 'The chat log contains a clear admission from the driver: "I know, I am sorry. I misjudged the timing." Running a red light is a serious safety violation. The driver has accepted responsibility. Safety incidents are escalated per safety_incident#5. A full refund has been issued and the case is escalated for human review of the driver\'s safety record. Note: the LLM was unavailable during processing; the deterministic rule outcome was used.',
      rule_outcome: {
        rule: { outcome: 'full_refund', refund_amount: 27.5, matched_rule_ids: [] },
        llm: { outcome: 'full_refund', refund_amount: 27.5 },
        disagreement: false,
        deciding_evidence_ids: ['chat_analysis:9'],
        deciding_policy_sections: ['safety_incident#5'],
        rejected_claims: [],
        rider_explanation: 'The driver admitted to running a red light. A full refund has been issued and the case is escalated for a safety review.',
        driver_explanation: 'You admitted to the violation. A human reviewer will determine the appropriate action regarding your driving privileges.',
        tone: 'empathetic',
        confidence_components: { agreement: 1.0, evidence_strength: 0.62, citation_validity: 0.8, history_risk: 0.15, fraud_penalty: 0.0 },
      },
      evidence_ids: ['chat_analysis:9', 'history_profile:9'],
      escalated: true,
      human_review_summary: {
        dispute: '#9 (safety_incident): Driver ran a red light. We could have been hit.',
        rider_brief: 'The rider reports the driver ran a red light. The driver admitted fault in the chat log.',
        driver_brief: 'The driver acknowledges the mistake and apologized.',
        key_evidence_ids: ['chat_analysis:9'],
        ruling: 'full_refund — refund $27.50 (confidence 0.68)',
        escalation_reason: 'safety_incident',
        recommended_action: 'The driver admitted to running a red light. Review the driver\'s safety record and determine if suspension is warranted.',
      },
      llm_degraded: true,
      created_at: ts(13, 11, 5),
    },
  },

  /* ---- #10: no-show, open (in progress) ---- */
  {
    id: 10, trip_id: 10, filed_by: 110,
    category: 'no_show',
    claim_text: 'Driver never showed up. I waited 10 minutes.',
    status: 'open', priority: 'normal',
    created_at: ts(14, 12, 0),
    outcome: null, refund_amount: null, llm_degraded: null,
    rider_opening: {
      sender: 'RiderAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The rider was charged a cancellation fee despite the driver not arriving.',
          argument_summary: 'The rider waited 10 minutes at the pickup location and the driver never arrived. GPS data shows the driver stopped 500 meters from the pickup. The rider requests a full refund of the $5.00 cancellation fee.',
          claims: [
            { text: 'The driver never arrived at the pickup location.', evidence_ids: ['noshow:10'], policy_section_ids: ['no_show_fee#2'] },
          ],
          requested_outcome: 'Full refund of the cancellation fee.',
          weaknesses: [],
        },
        round: 'opening',
      },
    },
    driver_opening: {
      sender: 'DriverAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver was en route when the rider cancelled.',
          argument_summary: 'The driver was heading to the pickup location when the rider cancelled. The driver was delayed by traffic but was making progress toward the pickup.',
          claims: [
            { text: 'The driver was en route and delayed by traffic.', evidence_ids: ['noshow:10'], policy_section_ids: ['no_show_fee#2'] },
          ],
          requested_outcome: 'No refund.',
          weaknesses: ['GPS shows the driver stopped 500 meters from the pickup.'],
        },
        round: 'opening',
      },
    },
  },

  /* ---- #11: route deviation, open (in progress) ---- */
  {
    id: 11, trip_id: 11, filed_by: 111,
    category: 'route_deviation',
    claim_text: 'Driver took a longer route. I was overcharged.',
    status: 'open', priority: 'normal',
    created_at: ts(14, 14, 0),
    outcome: null, refund_amount: null, llm_degraded: null,
    rider_opening: {
      sender: 'RiderAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The rider was overcharged due to a route deviation.',
          argument_summary: 'GPS evidence shows the actual route was 6.2 km while the optimal route was 4.8 km, a 29% deviation. This exceeds the 20% threshold in route_deviation#5. The rider was charged $38.00 for a trip that should have been shorter.',
          claims: [
            { text: 'The driver deviated by 29% from the optimal route.', evidence_ids: ['route_deviation:11', 'fare_validation:11'], policy_section_ids: ['route_deviation#5'] },
          ],
          requested_outcome: 'Partial refund for the excess distance.',
          weaknesses: [],
        },
        round: 'opening',
      },
    },
    driver_opening: {
      sender: 'DriverAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver took a necessary detour due to road closure.',
          argument_summary: 'The driver took a slightly longer route because the optimal path had a road closure. The deviation was necessary for safety.',
          claims: [
            { text: 'A road closure on the optimal route required a detour.', evidence_ids: ['route_deviation:11'], policy_section_ids: ['route_deviation#5'] },
          ],
          requested_outcome: 'No refund — the detour was necessary.',
          weaknesses: ['No road closure alerts are visible in the system for that route at that time.'],
        },
        round: 'opening',
      },
    },
  },

  /* ---- #12: route deviation, full refund ---- */
  {
    id: 12, trip_id: 12, filed_by: 112,
    category: 'route_deviation',
    claim_text: 'Driver took a completely wrong route, doubling the distance.',
    status: 'resolved', priority: 'high',
    created_at: ts(13, 11, 0),
    outcome: 'full_refund', refund_amount: 25.00, llm_degraded: false,
    rider_opening: {
      sender: 'RiderAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver took a route that nearly doubled the trip distance.',
          argument_summary: 'GPS evidence shows the actual route was 8.0 km while the optimal route was 4.5 km — a 78% deviation. This far exceeds the 20% threshold in route_deviation#5 and triggers the route_deviation_major rule. The rider was charged $25.00 for a trip that should have cost significantly less. A full refund is warranted.',
          claims: [
            { text: 'The driver deviated by 78% from the optimal route, triggering the major deviation rule.', evidence_ids: ['route_deviation:12', 'fare_validation:12'], policy_section_ids: ['route_deviation#5'] },
            { text: 'The fare was $25.00 for a trip that should have been approximately $14.00.', evidence_ids: ['fare_validation:12'], policy_section_ids: ['fare_discrepancy_5pct'] },
          ],
          requested_outcome: 'Full refund of $25.00.',
          weaknesses: [],
        },
        round: 'opening',
      },
    },
    driver_opening: {
      sender: 'DriverAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver followed GPS navigation which routed them incorrectly.',
          argument_summary: 'The driver states the navigation app routed them on a longer path. The driver was following the GPS and did not intentionally deviate. However, the platform\'s optimal route calculation shows the driver should have taken a more direct path.',
          claims: [
            { text: 'The driver followed GPS navigation which provided an incorrect route.', evidence_ids: ['route_deviation:12'], policy_section_ids: ['route_deviation#5'] },
          ],
          requested_outcome: 'Partial refund at most — the driver was following navigation.',
          weaknesses: ['The driver is responsible for following the platform\'s routing, not a third-party app.'],
        },
        round: 'opening',
      },
    },
    ruling: {
      id: 12, outcome: 'full_refund', refund_amount: 25.00,
      confidence: 0.93,
      reasoning: 'GPS evidence shows a 78% route deviation, triggering the route_deviation_major rule. The actual distance was 8.0 km versus the optimal 4.5 km. The fare validator confirms the rider was charged $25.00 for a trip that should have cost approximately $14.00. The driver\'s claim of following navigation does not override the platform\'s routing responsibility. A full refund of $25.00 is warranted.',
      rule_outcome: {
        rule: { outcome: 'full_refund', refund_amount: 25.0, matched_rule_ids: ['route_deviation_major', 'fare_discrepancy_5pct'] },
        llm: { outcome: 'full_refund', refund_amount: 25.0 },
        disagreement: false,
        deciding_evidence_ids: ['route_deviation:12', 'fare_validation:12'],
        deciding_policy_sections: ['route_deviation#5'],
        rejected_claims: [
          { advocate: 'DriverAdvocate', claim_text: 'The driver followed GPS navigation which provided an incorrect route.', reason: 'The driver is responsible for following the platform routing, not a third-party navigation app.' },
        ],
        rider_explanation: 'The GPS data shows the driver took a route nearly double the optimal distance. You are entitled to a full refund of $25.00.',
        driver_explanation: 'The route you took was significantly longer than the platform\'s optimal route. The rider has been fully refunded.',
        tone: 'empathetic',
        confidence_components: { agreement: 1.0, evidence_strength: 0.93, citation_validity: 1.0, history_risk: 0.05, fraud_penalty: 0.0 },
      },
      evidence_ids: ['route_deviation:12', 'fare_validation:12', 'history_profile:12'],
      escalated: false, human_review_summary: null, llm_degraded: false,
      created_at: ts(13, 11, 6),
    },
  },
]
