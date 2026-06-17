from aiogram.fsm.state import State, StatesGroup


class AddAdState(StatesGroup):
    """FSM для создания объявления."""
    ad_type = State()        # sale / rent
    category = State()       # выбор категории
    subcategory = State()    # выбор подкатегории
    photos = State()         # загрузка фото
    title = State()          # название
    price = State()          # цена
    city = State()           # город
    country = State()        # страна (опционально)
    condition = State()      # состояние
    size = State()           # размер (опционально)
    description = State()    # описание
    delivery_method = State()  # способ доставки
    contact_method = State()   # способ связи
    phone = State()          # телефон (если не telegram)
    confirm = State()        # подтверждение


class ReviewState(StatesGroup):
    """FSM для отзыва."""
    rating = State()
    comment = State()


class SearchState(StatesGroup):
    """FSM для поиска."""
    query = State()


class ModeratorRejectionState(StatesGroup):
    wait_for_reason = State()
