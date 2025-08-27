FROM python:3.10-slim

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 TZ=Asia/Seoul

# Chromium & chromedriver & 폰트 + 필요한 런타임
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    fonts-noto-cjk \
    libnss3 libxi6 libxrender1 libxcomposite1 \
    libxrandr2 libatk1.0-0 libatk-bridge2.0-0 libxdamage1 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    libxshmfence1 libx11-xcb1 libdrm2 libxfixes3 \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_BIN=/usr/bin/chromedriver \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gunicorn으로 실행 (Railway가 PORT 주입)
CMD ["sh","-c","gunicorn -k gthread -w 1 -b 0.0.0.0:${PORT:-8000} app:app --threads 2 --timeout 300 --log-level info"]
