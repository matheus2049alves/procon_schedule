# Monitor de Vagas - Procon MA

Este projeto é um bot automatizado para monitorar a disponibilidade de vagas de agendamento no site do Procon MA (Viva Cidadão). Ele verifica periodicamente as datas disponíveis para os próximos 10 dias e envia alertas via Telegram quando encontra horários livres.

## Funcionalidades

- **Monitoramento Contínuo**: Verifica vagas a cada 5 minutos.
- **Verificação Inteligente**:
  - Testa os próximos 10 dias (Ignora Domingos).
  - Identifica mensagens de erro ou indisponibilidade do site.
  - Pausa de 30 minutos após encontrar uma vaga para evitar alertas repetitivos.
- **Alertas via Telegram**: Envia notificação imediata com link direto para o agendamento.
- **Resiliência**: Tratamento de erros de conexão e verificação de integridade do ambiente.

## Pré-requisitos

- Python 3.11 ou superior
- [Poetry](https://python-poetry.org/) (Recomendado) ou pip

## Configuração

1. Clone o repositório.
2. Renomeie o arquivo `.env.example` para `.env` (se houver) ou crie um arquivo `.env` na raiz com o seguinte conteúdo:

```ini
TOKEN_TELEGRAM=seu_token_aqui
CHAT_ID=seu_chat_id_aqui
UNIDADE=85  # (Opcional) ID da unidade. Padrão 85 = Viva Penalva
SERVICO=316 # (Opcional) ID do serviço. Padrão 316 = RG Nacional (CIN)
```

## Instalação e Execução

### Usando Poetry (Recomendado)

```bash
# Instalar dependências
poetry install

# Verificar se tudo está correto
poetry run python tests/check_setup.py

# Rodar o monitor
poetry run python checker.py
```

### Usando pip/venv tradicional

```bash
# Criar/Ativar ambiente virtual
python -m venv .venv
# Windows: .\.venv\Scripts\Activate
# Linux/Mac: source .venv/bin/activate

# Instalar dependências
pip install requests python-dotenv

# Rodar
python checker.py
```

## Como funciona?

O script `checker.py` envia requisições simulando um navegador para o endpoint AJAX do sistema de agendamento. Ele analisa a resposta JSON/HTML para determinar se há vagas reais disponíveis, filtrando falsos positivos (mensagens de erro do site).

## Autor

Desenvolvido por **Matheus Costa Alves**.
