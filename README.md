# Pix Streaming API (Desafio Backend)

Este projeto é uma simulação de uma API para consumo de mensagens Pix em tempo real, inspirada nos princípios do SPI do Banco Central.

## 🔧 Tecnologias utilizadas

- Python 3.11+
- Django
- Django REST Framework
- SQLite (por enquanto)

## ▶️ Como rodar localmente

```bash
# Crie o ambiente virtual
python -m venv venv

# Ative o ambiente virtual
# Windows (cmd)
venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Rode as migrações
python manage.py migrate

# Rode o servidor local
python manage.py runserver
