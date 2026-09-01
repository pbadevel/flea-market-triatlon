"""
Файл - с моделями машины состояний
"""
from aiogram.fsm.state import StatesGroup, State


class AddAdState(StatesGroup):
    """
    Состояния для создания объявления
    """
    category = State()  # Выбор категории
    subcategory = State()  # Выбор подкатегории
    condition = State()  # Состояние
    title = State()  # Ввод названия (Марка\Бренд, модель)
    size = State()  # Размер
    description = State()  # Описание
    price = State()  # Ввод цены
    location_select = State()  # Выбор города/страны
    location_city_custom = State()  # Ввод собственного города
    location_country_custom = State()  # Ввод собственной страны
    location_city_after_country = State()  # Ввод города после выбора страны
    delivery_method = State()  # Выбор способа доставки (Самовывоз/Отправка)
    cover_photo = State()  # Загрузка обложки (1 фото)
    photos = State()  # Загрузка остальных фото (до 8 всего, включая обложку)
    contact_method = State()  # Выбор способа связи (Telegram/Phone)
    phone_input = State()  # Ввод номера телефона
    confirm = State()  # Подтверждение и отправка на модерацию


class ModerationState(StatesGroup):
    """
    Состояния для модерации
    """
    rejection_reason = State()  # Ввод причины отклонения
    comment = State()  # Ввод комментария (для одобрения и отклонения)


class ReviewState(StatesGroup):
    """
    Состояния для отзывов
    """
    comment = State()  # Ввод текста отзыва
    rating = State()  # Оценка


class SearchState(StatesGroup):
    """
    Состояния для поиска
    """
    query = State()  # Ввод поискового запроса
    custom_city_filter = State()  # Ввод города для фильтра
    custom_country_filter = State()  # Ввод страны для фильтра


class AdminPanelState(StatesGroup):
    """
    Состояния для админ-панели
    """
    # Объявления
    ads_menu = State()  # Меню объявлений
    delete_ad_input = State()  # Ввод номера объявления для удаления
    delete_ad_confirm = State()  # Подтверждение удаления
    edit_ad_input = State()  # Ввод номера объявления для редактирования
    edit_ad_menu = State()  # Меню редактирования объявления
    edit_ad_title = State()  # Редактирование названия
    edit_ad_description = State()  # Редактирование описания
    edit_ad_price = State()  # Редактирование цены
    edit_ad_city = State()  # Редактирование города (ввод вручную)
    edit_ad_city_select = State()  # Выбор города кнопками
    edit_ad_contact = State()  # Редактирование контакта (выбор способа)
    edit_ad_contact_phone = State()  # Ввод номера телефона при редактировании контакта
    view_ad_input = State()  # Ввод номера объявления для просмотра
    
    # Модераторы
    moderators_menu = State()  # Меню модераторов
    add_moderator_input = State()  # Ввод ID для добавления модератора
    remove_moderator_input = State()  # Ввод ID для удаления модератора

    # Управление пользователями (бан/разбан)
    user_management = State()
    ban_unban_input = State()  # Ввод @username или tg_id
    ban_unban_confirm = State()

    # Доверенный продавец
    trusted_seller_menu = State()
    trusted_seller_assign_input = State()  # Ввод @username или tg_id для назначения
    trusted_seller_assign_confirm = State()  # Подтверждение назначения
    trusted_seller_revoke_input = State()  # Ввод @username или tg_id для разжалования
    trusted_seller_revoke_confirm = State()  # Подтверждение разжалования

    # Статистика переходов
    stats_transitions = State()
    stats_transitions_period_input = State()  # Ввод интервала 30.01.2026-20.02.2026

    # Статистика за период
    stats_period_input = State()  # Ввод интервала 30.01.2026-20.02.2026
    stats_period_type = State()  # Выбор типа: Размещено/Продано/Снято/Рейтинги

    # Настройки поднятия (п.2.4)
    boost_settings_input = State()  # Ввод нового значения настройки

    # Автоподнятие — новый UI (п.2.4 доработка)
    auto_boost_interval_input = State()  # Ожидание ввода интервала (1–30 дней)
    auto_boost_count_input = State()     # Ожидание ввода кол-ва поднятий (1–5)


class PostAttachState(StatesGroup):
    """
    Состояния для команды /post_attach (пост в канал с кнопкой)
    """
    post_text = State()  # Текст поста
    post_button_text = State()  # Текст кнопки


class SupportState(StatesGroup):
    """
    Состояния для поддержки
    """
    message = State()  # Ввод сообщения в поддержку


class MyAdsState(StatesGroup):
    """
    Состояния для раздела "Мои объявления"
    """
    edit_menu = State()  # Меню редактирования
    edit_price = State()  # Редактирование цены
    edit_other = State()  # Меню редактирования других параметров
    edit_title = State()  # Редактирование названия
    edit_description = State()  # Редактирование описания
    edit_city = State()  # Редактирование города (текстовый ввод)
    edit_city_select = State()  # Выбор города из списка
    edit_city_custom = State()  # Ввод собственного города
    edit_city_after_country = State()  # Ввод города после выбора страны
    edit_category = State()  # Выбор категории
    edit_subcategory = State()  # Выбор подкатегории
    edit_size = State()  # Выбор размера
    edit_size_manual = State()  # Ввод размера вручную
    edit_cover_photo = State()  # Редактирование обложки (первое фото)
    edit_additional_photos = State()  # Редактирование остальных фото
    edit_photos = State()  # Редактирование фото (старое состояние, для совместимости)
    edit_contact = State()  # Выбор способа связи (Телеграмм / Телефон)
    edit_contact_phone = State()  # Ввод номера телефона при редактировании контакта