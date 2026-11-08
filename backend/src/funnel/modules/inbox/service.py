from funnel.modules.inbox.repository import OfferRepository


class OfferService:
    def __init__(self, repository: OfferRepository) -> None:
        self._repository = repository
