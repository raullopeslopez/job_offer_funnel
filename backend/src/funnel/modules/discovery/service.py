from funnel.modules.discovery.repository import SearchProfileRepository


class SearchProfileService:
    def __init__(self, repository: SearchProfileRepository) -> None:
        self._repository = repository
