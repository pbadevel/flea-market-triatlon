from sqlalchemy import select, or_, and_

from src.kit.repository.main import BaseRepository
from src.kit.repository.mixins import IDRepositoryMixin
from src.models import Media, Event, Action


class MediaRepository(BaseRepository[Media], IDRepositoryMixin[Media, int]):
    model = Media


    async def get_event_media_list(self, events: list[Event]) -> dict[int, list[str]]:
        """
        returns {event_id: [media_urls]}
        
        :param events: Description
        :type events: list[Event]
        """
        all_ids = []
        for event in events:
            all_ids.append((event.id, "event"))

        media_dict = {}

        if all_ids:
            media_ids = [id for id, _ in all_ids]
            
            media_stmt = select(Media).where(
                and_(Media.event_id.is_not(None), Media.event_id.in_(media_ids))
            )
            
            media_items = await self.get_all(media_stmt)
            
            for media in media_items:
                if media.event_id:
                    if media.event_id not in media_dict:
                        media_dict[media.event_id] = []
                    media_dict[media.event_id].append(media.safe_url)

        return media_dict
    

    async def get_action_media_list(self, actions: list[Action]) -> dict[int, list[str]]:
        """
        returns {action_ids: [media_urls]}
        
        :param events: Description
        :type events: list[Event]
        """
        all_ids = []
        for action in actions:
            all_ids.append((action.id, "action"))

        media_dict = {}

        if all_ids:
            media_ids = [id for id, _ in all_ids]
            
            media_stmt = select(Media).where(
                and_(Media.action_id.is_not(None), Media.action_id.in_(media_ids))
            )
            
            media_items = await self.get_all(media_stmt)
            
            for media in media_items:
                if media.action_id:
                    if media.action_id not in media_dict:
                        media_dict[media.action_id] = []
                    media_dict[media.action_id].append(media.safe_url)

        return media_dict

    