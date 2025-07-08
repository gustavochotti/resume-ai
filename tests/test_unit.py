# tests/test_unit.py
import sys
import os
from datetime import date, timedelta

# Adiciona o diretório raiz ao path para que possamos importar app.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import verificar_validade_assinatura

def test_assinatura_valida():
    """Testa se uma assinatura futura é considerada válida."""
    hoje = date.today()
    data_futura = hoje + timedelta(days=10)
    user_details = {'subscription_valid_until': data_futura.isoformat()}
    assert verificar_validade_assinatura(user_details) is True

def test_assinatura_expirada():
    """Testa se uma assinatura passada é considerada inválida."""
    hoje = date.today()
    data_passada = hoje - timedelta(days=1)
    user_details = {'subscription_valid_until': data_passada.isoformat()}
    assert verificar_validade_assinatura(user_details) is False

def test_assinatura_sem_data():
    """Testa se um perfil sem data de assinatura é considerado inválido."""
    user_details = {'name': 'Test User'}
    assert verificar_validade_assinatura(user_details) is False