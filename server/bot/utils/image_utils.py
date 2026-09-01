"""
Утилиты для работы с изображениями
"""

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import tempfile
from aiogram import Bot
from aiogram.types import FSInputFile
from loguru import logger


async def download_file_by_id(file_id: str, destination_path: str, bot: Bot):
    """Скачивает файл по file_id из Telegram"""
    file = await bot.get_file(file_id)
    await bot.download_file(file.file_path, destination_path)


async def add_logo_watermark_to_photo(file_id: str, chat_id: int, bot: Bot, logo_path: str = "assets/logo.png") -> str:
    """
    Обрезает изображение по центру, затем добавляет логотип и возвращает новый file_id
    
    Args:
        file_id: ID файла в Telegram
        chat_id: ID чата для отправки результата (для временного сообщения)
        bot: Экземпляр бота
        logo_path: Путь к файлу логотипа
        
    Returns:
        str: Новый file_id обработанного фото
    """
    temp_input_path = None
    temp_cropped_path = None
    temp_output_path = None
    
    try:
        # создаем временные файлы
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_input:
            temp_input_path = tmp_input.name
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_cropped:
            temp_cropped_path = tmp_cropped.name
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_output:
            temp_output_path = tmp_output.name
        
        # скачиваем файл
        await download_file_by_id(file_id=file_id, destination_path=temp_input_path, bot=bot)
        
        # открываем изображение
        img = Image.open(temp_input_path).convert("RGB")
        
        # СНАЧАЛА обрезаем изображение по центру (квадрат по меньшей стороне)
        width, height = img.size
        crop_size = min(width, height)
        left = (width - crop_size) // 2
        top = (height - crop_size) // 2
        right = left + crop_size
        bottom = top + crop_size
        img_cropped = img.crop((left, top, right, bottom))
        
        # Сохраняем обрезанное изображение во временный файл
        img_cropped.save(temp_cropped_path, quality=95)
        
        # Теперь открываем обрезанное изображение для наложения логотипа
        # Используем исходное изображение как фон (не белый, чтобы сохранить прозрачность логотипа)
        img = Image.open(temp_cropped_path).convert("RGB")
        # Создаем RGBA версию для наложения логотипа с прозрачностью
        img_rgba = img.convert("RGBA")
        wm = Image.new("RGBA", img_rgba.size, (255, 255, 255, 0))
        
        # добавляем логотип
        await _add_logo_watermark(img_rgba, wm, logo_path)
        
        # накладываем логотип на исходное изображение (прозрачные области логотипа останутся прозрачными)
        result = Image.alpha_composite(img_rgba, wm)
        # Конвертируем обратно в RGB, используя исходное изображение как фон
        # Это гарантирует, что прозрачные области логотипа не будут черными
        rgb = img.copy()  # Используем исходное изображение как основу
        # Накладываем результат с логотипом поверх исходного изображения
        # Прозрачные области логотипа не будут наложены, останется исходное изображение
        if result.mode == 'RGBA':
            rgb.paste(result, mask=result.split()[3])  # Используем альфа-канал как маску
        else:
            rgb.paste(result)
        rgb.save(temp_output_path, quality=95, format='JPEG')
        
        # отправляем обработанное фото (временно, чтобы получить file_id)
        mes = await bot.send_photo(
            chat_id=chat_id,
            photo=FSInputFile(temp_output_path)
        )
        
        # получаем file_id
        new_file_id = mes.photo[-1].file_id
        
        # удаляем временное сообщение
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mes.message_id)
        except Exception as e:
            logger.debug(f"не удалось удалить временное сообщение: {e}")
        
        # возвращаем новый file_id
        return new_file_id
        
    except Exception as e:
        logger.error(f"ошибка при добавлении логотипа: {e}", exc_info=True)
        # в случае ошибки возвращаем исходный file_id
        return file_id
    finally:
        # очистка временных файлов
        if temp_input_path and os.path.exists(temp_input_path):
            try:
                os.remove(temp_input_path)
            except:
                pass
        if temp_output_path and os.path.exists(temp_output_path):
            try:
                os.remove(temp_output_path)
            except:
                pass


async def _add_logo_watermark(img: Image.Image, wm: Image.Image, logo_path: str = None):
    """
    Добавляет водяную знак в виде логотипа в правом верхнем углу

    Args:
        img: Изображение для обработки
        wm: Слой водяного знака
        logo_path: Путь к файлу логотипа (если None, используется стандартный)
    """
    if logo_path is None:
        logo_path = "assets/logo.png"
    
    try:
        if not os.path.exists(logo_path):
            logger.error(f"файл логотипа не найден: {logo_path}")
            raise FileNotFoundError(f"файл логотипа не найден: {logo_path}")
        
        # открываем логотип
        logo = Image.open(logo_path).convert("RGBA")

        # Размер логотипа: ширина = 18% от ширины изображения (одинаковая ширина у всех логотипов на обложке)
        logo_size_ratio = 0.18
        max_logo_width = int(img.width * logo_size_ratio)
        scale = max_logo_width / logo.width
        new_logo_width = max_logo_width
        new_logo_height = int(logo.height * scale)
        logo = logo.resize((new_logo_width, new_logo_height), Image.Resampling.LANCZOS)

        # Прозрачность убрана: логотип накладывается без прозрачности для разных типов продажи
        # Прозрачные области PNG остаются прозрачными (не накладываются на изображение)

        # настройки отступов
        margin_x = 10  # Отступ от правого края
        margin_y = 10  # Отступ от верхнего края

        # позиция в правом верхнем углу
        position_x = img.width - logo.width - margin_x
        position_y = margin_y

        # вставляем логотип
        wm.paste(logo, (position_x, position_y), logo)

    except FileNotFoundError:
        logger.error(f"файл логотипа не найден: {logo_path}")
        raise
    except Exception as e:
        logger.error(f"ошибка при добавлении логотипа: {e}")
        raise


async def add_logo_to_image(image_bytes: bytes, logo_path: str = "assets/logo.png") -> bytes:
    """
    Добавляет логотип на изображение в правый верхний угол
    
    Args:
        image_bytes: Байты исходного изображения
        logo_path: Путь к файлу логотипа
        
    Returns:
        bytes: Байты изображения с логотипом
    """
    try:
        # Открываем исходное изображение
        image = Image.open(BytesIO(image_bytes))
        
        # Если логотип существует, добавляем его
        if os.path.exists(logo_path):
            logo = Image.open(logo_path)
            
            # Масштабируем логотип (18% от ширины изображения)
            logo_width = int(image.width * 0.18)
            logo_height = int(logo.height * (logo_width / logo.width))
            logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
            
            # Позиция логотипа (правый верхний угол с отступом)
            position = (image.width - logo_width - 20, 20)
            
            # Вставляем логотип
            if logo.mode == 'RGBA':
                image.paste(logo, position, logo)
            else:
                image.paste(logo, position)
        
        # Сохраняем результат в байты
        output = BytesIO()
        image.save(output, format='JPEG', quality=95)
        output.seek(0)
        return output.read()
    
    except Exception as e:
        # Если что-то пошло не так, возвращаем исходное изображение
        return image_bytes


async def add_trusted_seller_logo_to_photo(file_id: str, chat_id: int, bot: Bot, logo_path: str = "assets/logo.png") -> str:
    """
    Добавляет логотип доверенного продавца в левый верхний угол изображения
    
    Args:
        file_id: ID файла в Telegram
        chat_id: ID чата для отправки результата (для временного сообщения)
        bot: Экземпляр бота
        logo_path: Путь к файлу логотипа
        
    Returns:
        str: Новый file_id обработанного фото
    """
    temp_input_path = None
    temp_output_path = None
    
    try:
        # Создаем временные файлы
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_input:
            temp_input_path = tmp_input.name
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_output:
            temp_output_path = tmp_output.name
        
        # Скачиваем файл
        await download_file_by_id(file_id=file_id, destination_path=temp_input_path, bot=bot)
        
        # Открываем изображение
        img = Image.open(temp_input_path).convert("RGB")
        img_rgba = img.convert("RGBA")
        wm = Image.new("RGBA", img_rgba.size, (255, 255, 255, 0))
        
        # Добавляем логотип доверенного продавца в левый верхний угол
        if os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("RGBA")
            
            # Тот же размер, что и у логотипа Продажа/Аренда: ширина = 18% от ширины изображения
            logo_size_ratio = 0.18
            max_logo_width = int(img.width * logo_size_ratio)
            scale = max_logo_width / logo.width
            new_logo_width = max_logo_width
            new_logo_height = int(logo.height * scale)
            logo = logo.resize((new_logo_width, new_logo_height), Image.Resampling.LANCZOS)
            
            # Настройки отступов (левый верхний угол)
            margin_x = 10  # Отступ от левого края
            margin_y = 10  # Отступ от верхнего края
            
            # Позиция в левом верхнем углу
            position_x = margin_x
            position_y = margin_y
            
            # Вставляем логотип
            wm.paste(logo, (position_x, position_y), logo)
        
        # Накладываем логотип на изображение
        result = Image.alpha_composite(img_rgba, wm)
        rgb = img.copy()
        if result.mode == 'RGBA':
            rgb.paste(result, mask=result.split()[3])
        else:
            rgb.paste(result)
        rgb.save(temp_output_path, quality=95, format='JPEG')
        
        # Отправляем обработанное фото (временно, чтобы получить file_id)
        mes = await bot.send_photo(
            chat_id=chat_id,
            photo=FSInputFile(temp_output_path)
        )
        
        # Получаем file_id
        new_file_id = mes.photo[-1].file_id
        
        # Удаляем временное сообщение
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mes.message_id)
        except Exception as e:
            logger.debug(f"не удалось удалить временное сообщение: {e}")
        
        return new_file_id
    
    except Exception as e:
        logger.error(f"ошибка при добавлении логотипа доверенного продавца: {e}", exc_info=True)
        # В случае ошибки возвращаем исходный file_id
        return file_id
    
    finally:
        # Удаляем временные файлы
        for path in [temp_input_path, temp_output_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception as e:
                    logger.debug(f"не удалось удалить временный файл {path}: {e}")


async def crop_image_center(file_id: str, chat_id: int, bot: Bot) -> str:
    """
    Обрезает изображение квадратом по центру и возвращает новый file_id
    
    Args:
        file_id: ID файла в Telegram
        chat_id: ID чата для отправки результата (для временного сообщения)
        bot: Экземпляр бота
        
    Returns:
        str: Новый file_id обрезанного фото
    """
    temp_input_path = None
    temp_output_path = None
    
    try:
        # создаем временные файлы
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_input:
            temp_input_path = tmp_input.name
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_output:
            temp_output_path = tmp_output.name
        
        # скачиваем файл
        await download_file_by_id(file_id=file_id, destination_path=temp_input_path, bot=bot)
        
        # открываем изображение
        img = Image.open(temp_input_path).convert("RGB")
        
        # Определяем размер для обрезки (квадрат по меньшей стороне)
        width, height = img.size
        crop_size = min(width, height)
        
        # Вычисляем координаты для обрезки по центру
        left = (width - crop_size) // 2
        top = (height - crop_size) // 2
        right = left + crop_size
        bottom = top + crop_size
        
        # Обрезаем изображение
        img_cropped = img.crop((left, top, right, bottom))
        
        # Сохраняем обрезанное изображение
        img_cropped.save(temp_output_path, quality=95)
        
        # отправляем обработанное фото (временно, чтобы получить file_id)
        mes = await bot.send_photo(
            chat_id=chat_id,
            photo=FSInputFile(temp_output_path)
        )
        
        # получаем file_id
        new_file_id = mes.photo[-1].file_id
        
        # удаляем временное сообщение
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mes.message_id)
        except Exception as e:
            logger.debug(f"не удалось удалить временное сообщение: {e}")
        
        # возвращаем новый file_id
        return new_file_id
        
    except Exception as e:
        logger.error(f"ошибка при обрезке изображения: {e}", exc_info=True)
        # в случае ошибки возвращаем исходный file_id
        return file_id
    finally:
        # очистка временных файлов
        if temp_input_path and os.path.exists(temp_input_path):
            try:
                os.remove(temp_input_path)
            except:
                pass
        if temp_output_path and os.path.exists(temp_output_path):
            try:
                os.remove(temp_output_path)
            except:
                pass


async def create_ad_preview_image(image_bytes: bytes, text: str) -> bytes:
    """
    Создает превью объявления с текстом
    
    Args:
        image_bytes: Байты исходного изображения
        text: Текст для добавления
        
    Returns:
        bytes: Байты изображения с текстом
    """
    try:
        # Открываем изображение
        image = Image.open(BytesIO(image_bytes))
        
        # Создаем объект для рисования
        draw = ImageDraw.Draw(image)
        
        # Пытаемся загрузить шрифт
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        # Добавляем полупрозрачный фон для текста
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Позиция текста (внизу по центру)
        text_position = ((image.width - text_width) // 2, image.height - text_height - 30)
        
        # Рисуем фон для текста
        padding = 20
        background_bbox = [
            text_position[0] - padding,
            text_position[1] - padding,
            text_position[0] + text_width + padding,
            text_position[1] + text_height + padding
        ]
        
        overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(background_bbox, fill=(0, 0, 0, 180))
        
        # Накладываем overlay на изображение
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        image = Image.alpha_composite(image, overlay)
        
        # Рисуем текст
        draw = ImageDraw.Draw(image)
        draw.text(text_position, text, fill=(255, 255, 255), font=font)
        
        # Конвертируем обратно в RGB и сохраняем
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        
        output = BytesIO()
        image.save(output, format='JPEG', quality=95)
        output.seek(0)
        return output.read()
    
    except Exception as e:
        # В случае ошибки возвращаем исходное изображение
        return image_bytes
