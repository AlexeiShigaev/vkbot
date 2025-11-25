# Минимализм - наше все.
FROM python:3.12-slim

# целевая директория
WORKDIR /vkbot

# Копируем приложение
COPY . /vkbot

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Команда для запуска бота
CMD ["python", "-m /vkbot"]
