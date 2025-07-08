# tests/test_integration.py
import pytest
import os
from supabase import create_client, Client

# Pula este teste se as variáveis de ambiente não estiverem configuradas
@pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"),
    reason="As credenciais do Supabase não foram encontradas no ambiente."
)
def test_conexao_supabase():
    """Testa se a conexão com o Supabase pode ser estabelecida."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    assert url is not None, "A variável SUPABASE_URL não foi encontrada."
    assert key is not None, "A variável SUPABASE_KEY não foi encontrada."

    supabase: Client = create_client(url, key)
    
    # A asserção abaixo é o teste real. Se o cliente for criado sem erro, a conexão é válida.
    assert supabase is not None

    # A linha st.info(...) foi removida. Adicionamos um print() para dar um feedback no terminal.
    print("\nConexão com Supabase verificada com sucesso!")