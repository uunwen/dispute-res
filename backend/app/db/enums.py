import enum


class AccountRole(str, enum.Enum):
    rider = "rider"
    driver = "driver"


class DisputeCategory(str, enum.Enum):
    route_deviation = "route_deviation"
    no_show = "no_show"
    fare_dispute = "fare_dispute"
    property_damage = "property_damage"
    safety_incident = "safety_incident"


class RulingOutcome(str, enum.Enum):
    full_refund = "full_refund"
    partial_refund = "partial_refund"
    no_refund = "no_refund"
    favor_rider = "favor_rider"
    favor_driver = "favor_driver"


class AttachmentKind(str, enum.Enum):
    photo = "photo"
    receipt = "receipt"
    chat_log = "chat_log"
    other = "other"
