from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClaimedRouteJob:
    id: str
    account_id: str
    provider: str
    provider_message_id: str
    action: str
    destination_id: str
