FROM python:3.13-slim

WORKDIR /app

# Dependências de sistema
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    ca-certificates \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Node.js 22
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Verificação
RUN python --version \
    && pip --version \
    && node --version \
    && npm --version \
    && unzip -v | head -n 1

# Dependências Python
COPY requirements.txt .

RUN iconv -f UTF-16 -t UTF-8 requirements.txt > requirements-utf8.txt \
    && pip install --no-cache-dir -r requirements-utf8.txt

# Projeto
COPY . .

EXPOSE 3000

CMD ["reflex", "run", "--env", "prod", "--frontend-port", "3000"]