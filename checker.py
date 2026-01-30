import os
import time
import logging
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

# 0=SEG ... 6=DOM (igual ao JS do site)
SEMANA = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]

URL_AGENDAMENTO = "https://seati.segov.ma.gov.br/procon/agendamento/ajax.loading.horarios.php"
URL_SITE = "https://seati.segov.ma.gov.br/procon/agendamento/"

INTERVALO_ENTRE_DATAS = 1.5          # pausa curta entre checks de datas
INTERVALO_ENTRE_RODADAS = 300        # 5 minutos
INTERVALO_POS_ALERTA = 1800          # 30 minutos após alerta

# --- CONFIG E LOGS ---
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger(__name__)

TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
CHAT_ID = os.getenv("CHAT_ID")
UNIDADE = os.getenv("UNIDADE", "85")   # default: Viva Penalva
SERVICO = os.getenv("SERVICO", "316")  # default: RG Nacional (CIN)

if not TOKEN_TELEGRAM or not CHAT_ID:
    logger.critical("ERRO: Variáveis TOKEN_TELEGRAM ou CHAT_ID não definidas no .env.")
    raise SystemExit(1)

# Para evitar spam: só alerta 1x por data (nesta execução)
datas_alertadas: set[str] = set()

def enviar_alerta(mensagem: str) -> None:
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao enviar para Telegram: {e}")

def dia_semana_codigo(data_ddmmyyyy: str) -> str:
    d = datetime.strptime(data_ddmmyyyy, "%d/%m/%Y")
    return SEMANA[d.weekday()]

def montar_payload(unidade: str, servico: str, data_ddmmyyyy: str) -> list[tuple[str, str]]:
    # O backend espera dados[] em ordem:
    # dados[0]=unidade, dados[1]=servico, dados[2]=data, dados[3]=dia_semana
    day_code = dia_semana_codigo(data_ddmmyyyy)
    return [
        ("dados[]", unidade),
        ("dados[]", servico),
        ("dados[]", data_ddmmyyyy),
        ("dados[]", day_code),
    ]

def interpretar_resposta(response: requests.Response) -> tuple[bool, str]:
    """
    Retorna (tem_vaga, mensagem_status).
    Baseado no JS do site:
      - resposta é JSON em texto
      - error == "true" => indisponível (regra de negócio), msn explica
      - quando OK, deve ter atendimentos e horarios
    """
    try:
        data = response.json()
    except ValueError:
        # Se não vier JSON, loga um pedaço e considera "indefinido/sem vaga"
        snippet = (response.text or "").strip().replace("\n", " ")[:160]
        return False, f"Resposta não-JSON: {snippet}"

    if str(data.get("error", "")).lower() == "true":
        msn = str(data.get("msn", "")).strip()
        # Ex: "O agendamento ainda não está liberado para esta data"
        return False, msn or "Indisponível (error=true)"

    # Quando está OK
    atendimentos_raw = data.get("atendimentos", 0)
    try:
        atendimentos = int(atendimentos_raw)
    except (TypeError, ValueError):
        atendimentos = 0

    horarios = str(data.get("horarios", "")).strip()
    msn = str(data.get("msn", "")).strip()

    tem_vaga = atendimentos > 0 and horarios != "" and horarios != "00:00"
    if tem_vaga:
        return True, msn or "Horários disponíveis"
    return False, msn or "Sem vagas"

def verificar_vagas() -> bool:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": URL_SITE,
        "Origin": "https://seati.segov.ma.gov.br",
        "Accept": "text/plain, */*; q=0.01",
    }

    hoje = datetime.now()
    datas_para_testar = []
    
    # Próximos 10 dias, excluindo DOM (6)
    for i in range(1, 11):
        d = hoje + timedelta(days=i)
        if d.weekday() != 6: 
            datas_para_testar.append(d.strftime("%d/%m/%Y"))

    for data_ddmmyyyy in datas_para_testar:
        payload = montar_payload(UNIDADE, SERVICO, data_ddmmyyyy)

        try:
            r = requests.post(URL_AGENDAMENTO, data=payload, headers=headers, timeout=10)
            r.raise_for_status()

            tem_vaga, status_msg = interpretar_resposta(r)

            if tem_vaga:
                if data_ddmmyyyy in datas_alertadas:
                    logger.info(f"{data_ddmmyyyy}: Vaga detectada, mas já alertada nesta execução.")
                else:
                    datas_alertadas.add(data_ddmmyyyy)
                    logger.info(f"!!! VAGA EM {data_ddmmyyyy} !!! ({status_msg})")
                    enviar_alerta(
                        "🚨 VAGA ENCONTRADA!\n"
                        f"📅 Data: {data_ddmmyyyy}\n"
                        f"📍 Unidade: {UNIDADE}\n"
                        f"🧾 Serviço: {SERVICO}\n"
                        f"🔗 {URL_SITE}"
                    )
                return True

            # Sem vaga (ou não liberado) — loga o motivo
            logger.info(f"{data_ddmmyyyy}: {status_msg}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao testar {data_ddmmyyyy}: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao testar {data_ddmmyyyy}: {e}")

        time.sleep(INTERVALO_ENTRE_DATAS)

    return False

def main() -> None:
    logger.info("--- Monitor de Vagas Iniciado ---")
    logger.info(f"Unidade: {UNIDADE} | Serviço: {SERVICO}")

    while True:
        encontrou = verificar_vagas()
        if encontrou:
            logger.info(f"Aguardando {INTERVALO_POS_ALERTA//60} minutos após alerta...")
            time.sleep(INTERVALO_POS_ALERTA)
        else:
            logger.info(f"Aguardando {INTERVALO_ENTRE_RODADAS//60} minutos para a próxima rodada...")
            time.sleep(INTERVALO_ENTRE_RODADAS)

if __name__ == "__main__":
    main()
