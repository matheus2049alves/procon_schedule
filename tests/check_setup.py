import os
import sys
import requests
import logging
from dotenv import load_dotenv

# Ajuda a importar módulos do diretório pai
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from checker import dia_semana_codigo, URL_AGENDAMENTO, URL_SITE

# Configuração Básica
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("VERIFICADOR")

def test_environment():
    logger.info("--- 1. Verificando Variáveis de Ambiente ---")
    load_dotenv()
    
    required_vars = ["TOKEN_TELEGRAM", "CHAT_ID", "UNIDADE", "SERVICO"]
    missing = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            safe_val = value[:4] + "***" if "TOKEN" in var else value
            logger.info(f"✅ {var}: {safe_val}")
        else:
            logger.error(f"❌ {var}: NÃO DEFINIDO")
            missing.append(var)
            
    if missing:
        logger.error("ERRO: Configure as variáveis faltando no arquivo .env")
        return False
    return True

def test_telegram():
    logger.info("\n--- 2. Testando Conexão Telegram ---")
    token = os.getenv("TOKEN_TELEGRAM")
    chat_id = os.getenv("CHAT_ID")
    
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            bot_name = r.json().get("result", {}).get("first_name", "Desconhecido")
            logger.info(f"✅ Bot encontrado: {bot_name}")
            
            # Tentar enviar PING
            send_url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": "🔔 TESTE DE STARTUP: Sistema verificando conexões..."}
            rs = requests.post(send_url, json=payload, timeout=5)
            if rs.status_code == 200:
                logger.info("✅ Mensagem de teste enviada com sucesso!")
                return True
            else:
                logger.error(f"❌ Falha ao enviar mensagem: {rs.text}")
        else:
            logger.error("❌ Token inválido ou API do Telegram fora do ar.")
            
    except Exception as e:
        logger.error(f"❌ Erro de conexão com Telegram: {e}")
    
    return False

def test_procon_site():
    logger.info("\n--- 3. Testando Acesso ao Site Procon ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Bot Verificador 1.0)",
    }
    
    try:
        r = requests.get(URL_SITE, headers=headers, timeout=10)
        if r.status_code == 200:
            logger.info(f"✅ Site principal acessível ({r.status_code})")
        else:
            logger.warning(f"⚠️ Site principal retornou {r.status_code}")
            
        # Teste rápido no endpoint AJAX (pode retornar erro 200 com JSON de erro, o que é OK para conexão)
        r_ajax = requests.post(URL_AGENDAMENTO, data={}, headers=headers, timeout=10)
        if r_ajax.status_code == 200:
            logger.info(f"✅ Endpoint de agendamento acessível ({r_ajax.status_code})")
            return True
        else:
            logger.error(f"❌ Endpoint de agendamento inacessível: {r_ajax.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Erro ao conectar no site: {e}")
        
    return False

def test_logic():
    logger.info("\n--- 4. Testando Lógica de Datas ---")
    # Teste simples: Domingo (01/02/2026 seria domingo, por exemplo, mas vamos usar uma data fixa conhecida)
    # 30/01/2026 é sexta. 01/02/2026 é domingo.
    
    try:
        # Teste 1: Verificar se dia_semana_codigo não quebra
        exemplo = "30/01/2026"
        codigo = dia_semana_codigo(exemplo)
        if codigo == "SEX":
             logger.info(f"✅ Lógica de dia da semana OK ({exemplo} -> {codigo})")
        else:
             logger.error(f"❌ Erro na lógica de dia da semana: {exemplo} -> {codigo} (Esperado SEX)")
             return False
             
        # Teste 2: Simular loop de dias (apenas lógica, importando o código do arquivo principal ou replicando a lógica de filtro)
        # Como o filtro está dentro de verificar_vagas e não isolado, faremos um teste visual aqui da regra
        datas_filtradas = []
        from datetime import datetime, timedelta
        hoje = datetime.now()
        for i in range(1, 11):
            d = hoje + timedelta(days=i)
            # A REGRA É: Excluir DOMINGO (weekday 6)
            if d.weekday() != 6:
                datas_filtradas.append(d.strftime("%d/%m/%Y - %a"))
            else:
                logger.info(f" Domingo {d.strftime('%d/%m/%Y')} corretamente ignorado.")
        
        logger.info(f"✅ Dias que seriam verificados: {len(datas_filtradas)} de 10")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro no teste de lógica: {e}")
        return False

def run_all():
    checks = [
        test_environment,
        test_telegram,
        test_procon_site,
        test_logic
    ]
    
    success = True
    for check in checks:
        if not check():
            success = False
            
    print("\n" + "="*40)
    if success:
        print("🚀 TUDO PRONTO! O sistema parece saudável.")
        exit(0)
    else:
        print("⚠️ HOUVE PROBLEMAS. Verifique os logs acima.")
        exit(1)

if __name__ == "__main__":
    run_all()
