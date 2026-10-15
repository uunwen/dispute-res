import type { DisputeSpec } from './types'

/* ============================================================
 * Disputes #1–#6
 * ============================================================
 * #1: route_deviation, partial_refund
 * #2: route_deviation, no_refund
 * #3: no_show, full_refund
 * #4: no_show, no_refund
 * #5: no_show, partial_refund
 * #6: property_damage, escalated to human
 */

function ts(day: number, h: number, m: number): string {
  return new Date(2026, 9, day, h, m, 0).toISOString()
}

export const DISPUTES_1_6: DisputeSpec[] = [
  /* ---- #1: route deviation, partial refund ---- */
  {
    id: 1, trip_id: 1, filed_by: 101,
    category: 'route_deviation',
    claim_text: 'Driver took a much longer route than the GPS suggested, adding 3+ km to the trip.',
    status: 'resolved', priority: 'normal',
    created_at: ts(10, 10, 0),
    outcome: 'partial_refund', refund_amount: 8.50, llm_degraded: false,
    rider_opening: {
      sender: 'RiderAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The rider was overcharged due to an unnecessary route deviation.',
          argument_summary: 'GPS evidence shows the driver took a route 3.2 km longer than the optimal path computed by the system. The actual distance was 8.5 km versus the optimal 5.3 km, a 60% increase. The rider was charged $28.50 for a trip that should have cost approximately $20.00. Policy section route_deviation#5 states that deviations exceeding 20% warrant a refund of the excess fare.',
          claims: [
            { text: 'The driver deviated from the optimal route by 60%, far exceeding the 20% threshold in route_deviation#5.', evidence_ids: ['route_deviation:1', 'fare_validation:1'], policy_section_ids: ['route_deviation#5'] },
            { text: 'The rider was overcharged $8.50 for distance they did not need to travel.', evidence_ids: ['fare_validation:1'], policy_section_ids: ['fare_discrepancy_5pct'] },
          ],
          requested_outcome: 'Partial refund of $8.50 for the excess distance charge.',
          weaknesses: ['The driver may have been avoiding traffic, but GPS shows no congestion on the optimal route at that time.'],
        },
        round: 'opening',
      },
    },
    driver_opening: {
      sender: 'DriverAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver followed a reasonable route given traffic conditions.',
          argument_summary: 'The driver took a route that appeared longer but was necessary due to road construction on the optimal path. The deviation was not intentional and the driver exercised reasonable judgement. The fare was calculated by the platform meter, not the driver.',
          claims: [
            { text: 'Road construction on the optimal route made it impassable, forcing the detour.', evidence_ids: ['route_deviation:1'], policy_section_ids: ['route_deviation#5'] },
          ],
          requested_outcome: 'No refund — the route was reasonable under the circumstances.',
          weaknesses: ['GPS data does not show any construction alerts on the optimal route.'],
        },
        round: 'opening',
      },
    },
    ruling: {
      id: 1, outcome: 'partial_refund', refund_amount: 8.50,
      confidence: 0.87,
      reasoning: 'GPS evidence confirms a 60% route deviation, well above the 20% threshold defined in route_deviation#5. The driver claimed road construction but no construction alerts were present on the optimal route at the time of travel. The fare validator computed an excess of $8.50 over the expected fare. A partial refund of $8.50 is appropriate under the fare_discrepancy_5pct rule.',
      rule_outcome: {
        rule: { outcome: 'partial_refund', refund_amount: 8.50, matched_rule_ids: ['route_deviation_minor', 'fare_discrepancy_5pct'] },
        llm: { outcome: 'partial_refund', refund_amount: 8.50 },
        disagreement: false,
        deciding_evidence_ids: ['route_deviation:1', 'fare_validation:1'],
        deciding_policy_sections: ['route_deviation#5'],
        rejected_claims: [
          { advocate: 'DriverAdvocate', claim_text: 'Road construction on the optimal route made it impassable.', reason: 'No construction alerts found on the optimal route at the time of travel.' },
        ],
        rider_explanation: 'The GPS data clearly shows the driver took a longer route without justification. You are entitled to a partial refund for the excess distance charged.',
        driver_explanation: 'While you cited road construction, no alerts were active on the optimal route. The deviation resulted in an overcharge that the rider should not bear.',
        tone: 'empathetic',
        confidence_components: { agreement: 1.0, evidence_strength: 0.85, citation_validity: 1.0, history_risk: 0.15, fraud_penalty: 0.0 },
      },
      evidence_ids: ['route_deviation:1', 'fare_validation:1', 'history_profile:1'],
      escalated: false, human_review_summary: null, llm_degraded: false,
      created_at: ts(10, 10, 5),
    },
  },

  /* ---- #2: route deviation, no refund ---- */
  {
    id: 2, trip_id: 2, filed_by: 102,
    category: 'route_deviation',
    claim_text: 'Driver did not take the shortest route.',
    status: 'resolved', priority: 'low',
    created_at: ts(11, 15, 0),
    outcome: 'no_refund', refund_amount: 0.00, llm_degraded: false,
    rider_opening: {
      sender: 'RiderAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The rider believes the driver took a longer route than necessary.',
          argument_summary: 'GPS data shows the actual route was 0.4 km longer than the optimal route. While this is a deviation, it is relatively minor. The rider requests a review of the fare.',
          claims: [
            { text: 'The driver deviated by 0.4 km from the optimal route.', evidence_ids: ['route_deviation:2'], policy_section_ids: ['route_deviation#5'] },
          ],
          requested_outcome: 'Full refund of the fare.',
          weaknesses: ['The deviation is only 8%, below the 20% threshold in the policy.'],
        },
        round: 'opening',
      },
    },
    driver_opening: {
      sender: 'DriverAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver followed a reasonable route with only a minor deviation.',
          argument_summary: 'The route taken was only 0.4 km longer than optimal, an 8% deviation. This is well below the 20% threshold defined in route_deviation#5. The deviation was due to a one-way street that required a slight detour. No refund is warranted.',
          claims: [
            { text: 'The deviation was only 8%, below the 20% threshold for a refund.', evidence_ids: ['route_deviation:2'], policy_section_ids: ['route_deviation#5'] },
          ],
          requested_outcome: 'No refund.',
          weaknesses: [],
        },
        round: 'opening',
      },
    },
    ruling: {
      id: 2, outcome: 'no_refund', refund_amount: 0.00,
      confidence: 0.92,
      reasoning: 'The route deviation was 8%, well below the 20% threshold defined in route_deviation#5. The driver took a reasonable detour due to a one-way street. No refund is warranted under the current policy.',
      rule_outcome: {
        rule: { outcome: 'no_refund', refund_amount: 0.0, matched_rule_ids: ['route_deviation_minor'] },
        llm: { outcome: 'no_refund', refund_amount: 0.0 },
        disagreement: false,
        deciding_evidence_ids: ['route_deviation:2'],
        deciding_policy_sections: ['route_deviation#5'],
        rejected_claims: [
          { advocate: 'RiderAdvocate', claim_text: 'The driver deviated by 0.4 km from the optimal route.', reason: 'The 8% deviation is below the 20% threshold for a refund under route_deviation#5.' },
        ],
        rider_explanation: 'While the driver did take a slightly longer route, the deviation was minor and below the threshold that triggers a refund. The route was reasonable given the one-way street.',
        driver_explanation: 'The route you took was reasonable. The minor deviation does not warrant any refund.',
        tone: 'neutral',
        confidence_components: { agreement: 1.0, evidence_strength: 0.92, citation_validity: 1.0, history_risk: 0.10, fraud_penalty: 0.0 },
      },
      evidence_ids: ['route_deviation:2', 'history_profile:2'],
      escalated: false, human_review_summary: null, llm_degraded: false,
      created_at: ts(11, 15, 4),
    },
  },

  /* ---- #3: no-show, full refund ---- */
  {
    id: 3, trip_id: 3, filed_by: 103,
    category: 'no_show',
    claim_text: 'Driver never showed up. I waited 15 minutes and had to cancel.',
    status: 'resolved', priority: 'normal',
    created_at: ts(10, 9, 0),
    outcome: 'full_refund', refund_amount: 18.00, llm_degraded: false,
    rider_opening: {
      sender: 'RiderAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The rider was charged a no-show fee despite the driver never arriving.',
          argument_summary: 'GPS data shows the driver stopped 320 meters from the pickup location and never reached the rider. The driver did not arrive at the pickup point. The rider was charged an $18.00 cancellation fee. Policy section no_show_fee#2 states that if the driver does not arrive, the rider should receive a full refund of any cancellation fee.',
          claims: [
            { text: 'The driver never arrived at the pickup location.', evidence_ids: ['noshow:3'], policy_section_ids: ['no_show_fee#2'] },
            { text: 'The rider was charged an $18.00 cancellation fee unfairly.', evidence_ids: ['noshow:3'], policy_section_ids: ['no_show_driver_never_arrived'] },
          ],
          requested_outcome: 'Full refund of the $18.00 cancellation fee.',
          weaknesses: [],
        },
        round: 'opening',
      },
    },
    driver_opening: {
      sender: 'DriverAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver arrived at the pickup area but the rider did not come out.',
          argument_summary: 'The driver reached the vicinity of the pickup location and waited. The rider did not appear within the waiting period. The cancellation fee was applied per platform policy.',
          claims: [
            { text: 'The driver arrived near the pickup location.', evidence_ids: ['noshow:3'], policy_section_ids: ['no_show_fee#2'] },
          ],
          requested_outcome: 'No refund — the rider was a no-show.',
          weaknesses: ['GPS shows the driver was 320 meters from the exact pickup point.'],
        },
        round: 'opening',
      },
    },
    ruling: {
      id: 3, outcome: 'full_refund', refund_amount: 18.00,
      confidence: 0.91,
      reasoning: 'GPS evidence shows the driver stopped 320 meters from the exact pickup coordinates and never reached the rider. The no_show_driver_never_arrived rule is applicable: the driver did not arrive at the pickup point. The $18.00 cancellation fee was charged in error and should be fully refunded.',
      rule_outcome: {
        rule: { outcome: 'full_refund', refund_amount: 18.0, matched_rule_ids: ['no_show_driver_never_arrived'] },
        llm: { outcome: 'full_refund', refund_amount: 18.0 },
        disagreement: false,
        deciding_evidence_ids: ['noshow:3'],
        deciding_policy_sections: ['no_show_fee#2'],
        rejected_claims: [
          { advocate: 'DriverAdvocate', claim_text: 'The driver arrived near the pickup location.', reason: 'GPS shows the driver was 320 meters from the exact pickup coordinates, which does not constitute arrival.' },
        ],
        rider_explanation: 'The GPS data confirms the driver never reached your pickup location. You are entitled to a full refund of the cancellation fee.',
        driver_explanation: 'The driver did not reach the exact pickup coordinates. The cancellation fee has been refunded to the rider.',
        tone: 'empathetic',
        confidence_components: { agreement: 1.0, evidence_strength: 0.91, citation_validity: 1.0, history_risk: 0.08, fraud_penalty: 0.0 },
      },
      evidence_ids: ['noshow:3', 'history_profile:3'],
      escalated: false, human_review_summary: null, llm_degraded: false,
      created_at: ts(10, 9, 4),
    },
  },

  /* ---- #4: no-show, no refund ---- */
  {
    id: 4, trip_id: 4, filed_by: 104,
    category: 'no_show',
    claim_text: 'I was charged a no-show fee but the driver was late.',
    status: 'resolved', priority: 'low',
    created_at: ts(11, 11, 0),
    outcome: 'no_refund', refund_amount: 0.00, llm_degraded: false,
    rider_opening: {
      sender: 'RiderAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The rider claims the driver was late and the no-show fee is unfair.',
          argument_summary: 'The rider states the driver arrived late to the pickup area and the rider had already left. The rider was charged a $5.00 cancellation fee. However, the rider cancelled the trip before the driver arrived.',
          claims: [
            { text: 'The driver was late arriving at the pickup.', evidence_ids: ['noshow:4'], policy_section_ids: ['no_show_fee#2'] },
          ],
          requested_outcome: 'Full refund of the $5.00 fee.',
          weaknesses: ['The rider cancelled before the driver reached the pickup area.'],
        },
        round: 'opening',
      },
    },
    driver_opening: {
      sender: 'DriverAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The rider cancelled before the driver arrived and the fee is per policy.',
          argument_summary: 'The driver was en route to the pickup when the rider cancelled. GPS shows the driver was 800 meters from the pickup. The rider did not wait the required period. The no_show_rider_waited rule applies: the rider must wait the full waiting period before cancelling without penalty.',
          claims: [
            { text: 'The rider cancelled before the driver arrived, violating the waiting period policy.', evidence_ids: ['noshow:4'], policy_section_ids: ['no_show_fee#2'] },
          ],
          requested_outcome: 'No refund — the fee is per policy.',
          weaknesses: [],
        },
        round: 'opening',
      },
    },
    ruling: {
      id: 4, outcome: 'no_refund', refund_amount: 0.00,
      confidence: 0.88,
      reasoning: 'GPS evidence shows the rider cancelled the trip while the driver was still 800 meters from the pickup location. The rider did not wait the required period defined in no_show_fee#2. The no_show_rider_waited rule indicates the cancellation fee is valid when the rider cancels prematurely. No refund is warranted.',
      rule_outcome: {
        rule: { outcome: 'no_refund', refund_amount: 0.0, matched_rule_ids: ['no_show_rider_waited'] },
        llm: { outcome: 'no_refund', refund_amount: 0.0 },
        disagreement: false,
        deciding_evidence_ids: ['noshow:4'],
        deciding_policy_sections: ['no_show_fee#2'],
        rejected_claims: [
          { advocate: 'RiderAdvocate', claim_text: 'The driver was late arriving at the pickup.', reason: 'The rider cancelled before the driver arrived and before the required waiting period elapsed.' },
        ],
        rider_explanation: 'The driver was still en route when you cancelled. The cancellation fee is valid under the platform policy since you did not wait the required period.',
        driver_explanation: 'The rider cancelled prematurely. The cancellation fee was correctly applied.',
        tone: 'neutral',
        confidence_components: { agreement: 1.0, evidence_strength: 0.88, citation_validity: 1.0, history_risk: 0.25, fraud_penalty: 0.0 },
      },
      evidence_ids: ['noshow:4', 'history_profile:4'],
      escalated: false, human_review_summary: null, llm_degraded: false,
      created_at: ts(11, 11, 3),
    },
  },

  /* ---- #5: no-show, partial refund ---- */
  {
    id: 5, trip_id: 5, filed_by: 105,
    category: 'no_show',
    claim_text: 'Driver said they arrived but I was already outside waiting.',
    status: 'resolved', priority: 'normal',
    created_at: ts(12, 17, 0),
    outcome: 'partial_refund', refund_amount: 8.25, llm_degraded: false,
    rider_opening: {
      sender: 'RiderAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The rider waited outside but the driver claimed they arrived and left.',
          argument_summary: 'GPS data shows the driver arrived approximately 50 meters from the pickup location. The driver waited 2.5 minutes and then cancelled. The rider was outside waiting the entire time but the driver may have gone to the wrong entrance. A partial refund is warranted because the driver did wait briefly but did not make contact.',
          claims: [
            { text: 'The driver arrived near the pickup but did not make contact with the rider.', evidence_ids: ['noshow:5'], policy_section_ids: ['no_show_fee#2'] },
            { text: 'The driver only waited 2.5 minutes, which is shorter than the expected waiting period.', evidence_ids: ['noshow:5'], policy_section_ids: ['no_show_rider_waited'] },
          ],
          requested_outcome: 'Partial refund of the $16.50 fare.',
          weaknesses: ['The driver did arrive in the vicinity of the pickup.'],
        },
        round: 'opening',
      },
    },
    driver_opening: {
      sender: 'DriverAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver arrived and waited but the rider did not appear.',
          argument_summary: 'The driver arrived at the pickup location and waited 2.5 minutes. The rider did not come to the vehicle. The driver followed protocol and the cancellation fee is valid.',
          claims: [
            { text: 'The driver arrived and waited the required time.', evidence_ids: ['noshow:5'], policy_section_ids: ['no_show_fee#2'] },
          ],
          requested_outcome: 'No refund.',
          weaknesses: ['The driver waited only 2.5 minutes, which may be shorter than the standard waiting period.'],
        },
        round: 'opening',
      },
    },
    ruling: {
      id: 5, outcome: 'partial_refund', refund_amount: 8.25,
      confidence: 0.79,
      reasoning: 'The driver arrived within 50 meters of the pickup but waited only 2.5 minutes, which is shorter than the standard 5-minute waiting period referenced in no_show_fee#2. Both parties share some responsibility: the driver did arrive but did not wait long enough, and the rider may have been at a different entrance. A partial refund of 50% ($8.25) is appropriate.',
      rule_outcome: {
        rule: { outcome: 'partial_refund', refund_amount: 8.25, matched_rule_ids: ['no_show_rider_waited'] },
        llm: { outcome: 'partial_refund', refund_amount: 8.25 },
        disagreement: false,
        deciding_evidence_ids: ['noshow:5'],
        deciding_policy_sections: ['no_show_fee#2'],
        rejected_claims: [],
        rider_explanation: 'The driver did arrive near your location but did not wait the full period. A partial refund has been issued.',
        driver_explanation: 'While you did arrive, the waiting period was shorter than the standard 5 minutes. A partial refund has been issued to the rider.',
        tone: 'empathetic',
        confidence_components: { agreement: 1.0, evidence_strength: 0.79, citation_validity: 1.0, history_risk: 0.12, fraud_penalty: 0.0 },
      },
      evidence_ids: ['noshow:5', 'history_profile:5'],
      escalated: false, human_review_summary: null, llm_degraded: false,
      created_at: ts(12, 17, 4),
    },
  },

  /* ---- #6: property damage, escalated ---- */
  {
    id: 6, trip_id: 6, filed_by: 106,
    category: 'property_damage',
    claim_text: 'Driver scratched my luggage while loading it into the trunk.',
    status: 'needs_human_review', priority: 'high',
    created_at: ts(10, 10, 30),
    outcome: 'partial_refund', refund_amount: 15.00, llm_degraded: false,
    rider_opening: {
      sender: 'RiderAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The rider\'s luggage was damaged during loading by the driver.',
          argument_summary: 'The rider reports that their luggage was scratched while the driver loaded it into the trunk. Chat analysis shows the rider immediately reported the damage and the driver denied responsibility. There are no photos of the damage. Policy section safety_incident#5 covers property damage during a trip and allows for compensation.',
          claims: [
            { text: 'The driver damaged the rider\'s luggage during loading.', evidence_ids: ['chat_analysis:6'], policy_section_ids: ['safety_incident#5'] },
            { text: 'The rider reported the damage immediately in the trip chat.', evidence_ids: ['chat_analysis:6'], policy_section_ids: ['general_principles#4'] },
          ],
          requested_outcome: 'Compensation for the damaged luggage.',
          weaknesses: ['No photo evidence of the damage was provided.'],
        },
        round: 'opening',
      },
    },
    driver_opening: {
      sender: 'DriverAdvocate', recipient: 'Judge', message_type: 'case_brief',
      content: {
        brief: {
          position: 'The driver denies causing damage to the luggage.',
          argument_summary: 'The driver states the luggage was already scratched when the rider handed it over. The driver loaded the luggage carefully and did not cause any damage. There is no photographic evidence to support the rider\'s claim.',
          claims: [
            { text: 'The luggage was already damaged when the rider handed it over.', evidence_ids: ['chat_analysis:6'], policy_section_ids: ['general_principles#4'] },
          ],
          requested_outcome: 'No compensation.',
          weaknesses: ['There is no evidence the luggage was pre-damaged.'],
        },
        round: 'opening',
      },
    },
    escalation: {
      sender: 'Judge', recipient: 'HumanReviewer', message_type: 'escalation',
      content: {
        dispute: '#6 (property_damage): Driver scratched my luggage while loading it into the trunk.',
        rider_brief: 'The rider reports luggage damage during loading and reported it immediately in chat. No photos provided.',
        driver_brief: 'The driver denies causing the damage and claims the luggage was pre-scratched. No evidence of pre-existing damage.',
        key_evidence_ids: ['chat_analysis:6'],
        ruling: 'partial_refund — refund $15.00 (confidence 0.65)',
        escalation_reason: 'safety_incident',
        recommended_action: 'Review the chat log and determine whether the rider should provide photo evidence. The provisional ruling is a partial refund of $15.00.',
      },
    },
    ruling: {
      id: 6, outcome: 'partial_refund', refund_amount: 15.00,
      confidence: 0.65,
      reasoning: 'The rider reported luggage damage immediately in the trip chat, which supports the claim. However, no photographic evidence was provided and the driver denies responsibility. Property damage cases without photo evidence require human review. A provisional partial refund of $15.00 has been issued pending human review.',
      rule_outcome: {
        rule: { outcome: 'partial_refund', refund_amount: 15.0, matched_rule_ids: [] },
        llm: { outcome: 'partial_refund', refund_amount: 15.0 },
        disagreement: false,
        deciding_evidence_ids: ['chat_analysis:6'],
        deciding_policy_sections: ['safety_incident#5'],
        rejected_claims: [],
        rider_explanation: 'Your immediate report in the chat supports your claim. However, photo evidence is needed for a final decision.',
        driver_explanation: 'You denied the damage, but the rider reported it immediately. A human reviewer will make the final determination.',
        tone: 'empathetic',
        confidence_components: { agreement: 1.0, evidence_strength: 0.55, citation_validity: 0.8, history_risk: 0.10, fraud_penalty: 0.0 },
      },
      evidence_ids: ['chat_analysis:6', 'history_profile:6'],
      escalated: true,
      human_review_summary: {
        dispute: '#6 (property_damage): Driver scratched my luggage while loading it into the trunk.',
        rider_brief: 'The rider reports luggage damage during loading and reported it immediately in chat. No photos provided.',
        driver_brief: 'The driver denies causing the damage and claims the luggage was pre-scratched. No evidence of pre-existing damage.',
        key_evidence_ids: ['chat_analysis:6'],
        ruling: 'partial_refund — refund $15.00 (confidence 0.65)',
        escalation_reason: 'safety_incident',
        recommended_action: 'Review the chat log and determine whether the rider should provide photo evidence. The provisional ruling is a partial refund of $15.00.',
      },
      llm_degraded: false,
      created_at: ts(10, 10, 35),
    },
  },
]
