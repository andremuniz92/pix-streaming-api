# Pix Streaming API (Desafio Backend)

Uma implementação robusta de API para coleta de mensagens Pix em tempo real, baseada nos princípios da Interface de Comunicação do SPI (Sistema de Pagamentos Instantâneos) do Banco Central do Brasil.

## Sobre o Projeto

Este projeto foi desenvolvido como resposta a um desafio técnico que simula um sistema de alto volume para gerenciamento de mensagens Pix. A solução implementa um mecanismo de streaming com funcionalidades como long polling, controle de sessões simultâneas e isolamento de dados por instituição financeira (ISPB).

### Contexto do Desafio

O sistema foi projetado para atender aos requisitos de uma aplicação back-end que processa mensagens Pix com as seguintes características:

- **Alto volume de transações**: Capacidade de processar múltiplas mensagens simultaneamente
- **Streaming em tempo real**: Implementação de long polling para entrega eficiente de mensagens
- **Controle de concorrência**: Limite de até 6 coletores simultâneos por ISPB
- **Isolamento de dados**: Garantia de que mensagens sejam entregues apenas para o ISPB correto
- **Prevenção de duplicação**: Mecanismo para evitar que a mesma mensagem seja entregue múltiplas vezes

## 🏗️ Arquitetura e Decisões Técnicas

### Tecnologias Utilizadas

**Framework Principal:**
- **Django 5.2.2**: Framework web para Python
- **Django REST Framework**: Extensão especializada para APIs REST com recursos avançados de serialização e renderização

**Banco de Dados:**
- **PostgreSQL**: Banco de dados relacional escolhido 
- **Migração do SQLite**: O projeto inicialmente utilizava SQLite para desenvolvimento local, mas foi migrado para PostgreSQL para melhor performance e recursos de produção

**Containerização:**
- **Docker**: Containerização da aplicação para garantir consistência entre ambientes
- **Docker Compose**: Orquestração dos serviços (aplicação + banco de dados)

### Decisões de Design

**Padrão de Renderização Customizada:**
A implementação utiliza um renderizador personalizado (`MultipartJsonRenderer`) para lidar com o cabeçalho `Accept: multipart/json`, que retorna um array JSON com múltiplas mensagens, diferentemente do comportamento padrão que retorna uma única mensagem para `Accept: application/json`.

**Arquitetura de Classes Base:**
Foi implementada uma classe base `PixStreamBaseView` que centraliza a lógica comum entre os endpoints de início e continuação de stream, promovendo reutilização de código e manutenibilidade.

**Controle de Sessões:**
O sistema utiliza o modelo `StreamSession` para controlar sessões ativas, implementando o limite de 6 coletores simultâneos por ISPB e garantindo que mensagens não sejam duplicadas entre streams diferentes.

## Funcionalidades Implementadas

### Endpoints da API

**1. Iniciar Stream de Mensagens**
```
GET /api/pix/{ispb}/stream/start
```
- Inicia um novo stream de coleta de mensagens para um ISPB específico.
- **Comportamento do cabeçalho `Accept`:**
  - Se `Accept: application/json` (ou cabeçalho ausente), a API retorna **uma única mensagem Pix** como um objeto JSON.
  - Se `Accept: multipart/json`, a API retorna **múltiplas mensagens Pix** (até 10) como um array JSON.
- Implementa verificação de limite de sessões ativas (máximo 6 por ISPB).
- Retorna o cabeçalho `Pull-Next` com o `interactionId` para continuar o stream.

**2. Continuar Stream Existente**
```
GET /api/pix/{ispb}/stream/{interactionId}
```
- Continua um stream existente usando o `interactionId` fornecido no cabeçalho `Pull-Next` de uma requisição anterior.
- **Comportamento do cabeçalho `Accept`:**
  - Se `Accept: application/json`, a API retorna **uma única mensagem Pix** como um objeto JSON.
  - Se `Accept: multipart/json`, a API retorna **múltiplas mensagens Pix** (até 10) como um array JSON.
- Mantém o mesmo comportamento do endpoint de início, mas sem verificação de limite de sessões (já que a sessão já foi estabelecida).
- Permite continuidade do fluxo de coleta de mensagens.
- Retorna o cabeçalho `Pull-Next` com um novo `interactionId` para a próxima requisição.

**3. Finalizar Stream**
```
DELETE /api/pix/{ispb}/stream/{interactionId}
```
- Finaliza um stream ativo, liberando recursos para outros coletores.
- Implementa idempotência (retorna sucesso mesmo se o stream não existir).
- Essencial para o gerenciamento adequado de recursos do sistema.

### Características Técnicas Avançadas

**Long Polling:**
O sistema implementa long polling com timeout de 8 segundos. Quando não há mensagens disponíveis, a API aguarda por novos dados antes de retornar uma resposta `204 No Content`, otimizando a eficiência da comunicação cliente-servidor.

**Controle de Concorrência:**
Cada ISPB pode ter no máximo 6 streams ativos simultaneamente. Tentativas de criar streams adicionais resultam em erro `429 Too Many Requests`, garantindo que o sistema não seja sobrecarregado.

**Isolamento de Dados:**
As mensagens são filtradas rigorosamente por ISPB do recebedor, garantindo que cada instituição tenha acesso apenas às suas próprias transações.

**Prevenção de Duplicação:**
Utiliza o campo `claimed_by_stream` para marcar mensagens já processadas, implementado dentro de transações atômicas para garantir consistência em cenários de alta concorrência.

## Instalação e Execução

### Pré-requisitos

- Docker e Docker Compose instalados
- Git para clonar o repositório

### Executando com Docker (Recomendado)

O projeto está completamente containerizado com PostgreSQL como banco de dados:

```bash
# Clone o repositório
git clone <url-do-repositorio>
cd pix-streaming-api

# Execute com Docker Compose (primeira vez)
docker-compose up --build

# Para execuções subsequentes
docker-compose up

# A API estará disponível em http://localhost:8000
```

**Configuração do Ambiente:**
- **Container da aplicação**: `selecao_web` (porta 8000)
- **Container do banco**: `selecao_db` (PostgreSQL 15)
- **Variáveis de ambiente**: Configuradas automaticamente no docker-compose.yml

**Comandos úteis:**

```bash
# Executar em background
docker-compose up -d

# Ver logs da aplicação
docker-compose logs web

# Parar os serviços
docker-compose down

# Executar migrações (se necessário)
docker-compose exec web python manage.py migrate

# Criar superusuário
docker-compose exec web python manage.py createsuperuser

# Executar testes
docker-compose exec web python manage.py test streaming
```

### Executando Localmente (Desenvolvimento)

Para desenvolvimento local sem Docker:

```bash
# Crie o ambiente virtual
python -m venv venv

# Ative o ambiente virtual
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt

# Configure o banco de dados (SQLite para desenvolvimento local)
python manage.py migrate

# Execute o servidor de desenvolvimento
python manage.py runserver
```

**Nota:** Para desenvolvimento local, o projeto usará SQLite por padrão. Para usar PostgreSQL localmente, configure as variáveis de ambiente conforme o docker-compose.yml.

## Testes Automatizados

O projeto inclui uma suite completa de testes automatizados cobrindo tanto testes de integração quanto testes unitários.

### Executando os Testes

**Com Docker (Recomendado):**
```bash
# Executar todos os testes
docker-compose exec web python manage.py test streaming

# Executar apenas testes de integração
docker-compose exec web python manage.py test streaming.tests.PixStreamAPITests

# Executar apenas testes unitários
docker-compose exec web python manage.py test streaming.tests.PixStreamUnitTests
```

**Localmente:**
```bash
# Executar todos os testes
python manage.py test streaming

# Executar apenas testes de integração
python manage.py test streaming.tests.PixStreamAPITests

# Executar apenas testes unitários
python manage.py test streaming.tests.PixStreamUnitTests
```

### Cobertura de Testes

**Testes de Integração (12 testes):**
- Funcionamento completo dos três endpoints
- Diferentes formatos de resposta (`application/json` vs `multipart/json`)
- Long polling e resposta `204 No Content`
- Controle de limite de sessões e erro `429`
- Fluxo completo de streaming (start → continue → delete)
- Isolamento entre ISPBs diferentes
- Prevenção de duplicação de mensagens

**Testes Unitários (6 testes):**
- Funções auxiliares (`random_string`, `random_cpf_cnpj`)
- Criação e validação de models (`PixMessage`, `StreamSession`)
- Comportamento de componentes isolados

## Documentação da API

### Formato de Resposta das Mensagens

Todas as mensagens Pix seguem o formato padronizado baseado na especificação do SPI:

```json
{
  "endToEndId": "E320749862024022119277T3lEBbUM0z",
  "valor": 90.20,
  "pagador": {
    "nome": "Marcos José",
    "cpfCnpj": "98716278190",
    "ispb": "32074986",
    "agencia": "0001",
    "contaTransacional": "1231231",
    "tipoConta": "CACC"
  },
  "recebedor": {
    "nome": "Flavio José",
    "cpfCnpj": "77615678291",
    "ispb": "00000000",
    "agencia": "0361",
    "contaTransacional": "1210098",
    "tipoConta": "SVGS"
  },
  "campoLivre": "",
  "txId": "h7a786d8a7s6gd1hgs",
  "dataHoraPagamento": "2022-07-23T19:47:18.108Z"
}
```

### Exemplos de Uso

**Iniciando um Stream (Mensagem Única):**
```bash
curl --location 'http://localhost:8000/api/pix/32074986/stream/start' \
--header 'Accept: application/json'
```

**Resposta (200 OK):**
```json
{
  "endToEndId": "E320749862024022119277T3lEBbUM0z",
  "valor": 90.20,
  "pagador": { ... },
  "recebedor": { ... },
  "campoLivre": "",
  "txId": "h7a786d8a7s6gd1hgs",
  "dataHoraPagamento": "2022-07-23T19:47:18.108Z"
}
```

**Headers de Resposta:**
```
Pull-Next: /api/pix/32074986/stream/5oj7tm0jow61
```

**Iniciando um Stream (Múltiplas Mensagens):**
```bash
curl --location 'http://localhost:8000/api/pix/32074986/stream/start' \
--header 'Accept: multipart/json'
```

**Resposta (200 OK):**
```json
[
  {
    "endToEndId": "E320749862024022119277T3lEBbUM0z",
    "valor": 90.20,
    "pagador": { ... },
    "recebedor": { ... },
    "campoLivre": "",
    "txId": "h7a786d8a7s6gd1hgs",
    "dataHoraPagamento": "2022-07-23T19:47:18.108Z"
  },
  {
    "endToEndId": "E320749862024022119277T3lEBbUM0z2",
    "valor": 150.75,
    "pagador": { ... },
    "recebedor": { ... },
    "campoLivre": "",
    "txId": "h7a786d8a7s6gd1hgs2",
    "dataHoraPagamento": "2022-07-23T19:48:22.315Z"
  }
]
```

**Continuando um Stream:**
```bash
curl --location 'http://localhost:8000/api/pix/32074986/stream/5oj7tm0jow61' \
--header 'Accept: application/json'
```

**Finalizando um Stream:**
```bash
curl -X DELETE 'http://localhost:8000/api/pix/32074986/stream/5oj7tm0jow61'
```

**Resposta (200 OK):**
```json
{}
```

### Códigos de Status

| Código | Descrição | Cenário |
|--------|-----------|---------|
| 200 | OK | Mensagens encontradas e retornadas |
| 204 | No Content | Nenhuma mensagem disponível após long polling |
| 429 | Too Many Requests | Limite de 6 sessões ativas atingido |
| 406 | Not Acceptable | Cabeçalho Accept não suportado |

## Utilitários de Desenvolvimento

### Gerando Mensagens de Teste

O projeto inclui um endpoint utilitário para gerar mensagens Pix para testes:

```bash
# Gerar 10 mensagens para o ISPB 32074986
curl -X POST http://localhost:8000/api/util/msgs/32074986/10
```

### Acessando o Admin do Django

**Com Docker:**
```bash
# Criar superusuário
docker-compose exec web python manage.py createsuperuser

# Acessar admin em http://localhost:8000/admin/
```

**Localmente:**
```bash
# Criar superusuário
python manage.py createsuperuser

# Acessar admin em http://localhost:8000/admin/
```
