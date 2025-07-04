import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from io import BytesIO
from youtube_transcript_api import YouTubeTranscriptApi
from newspaper import Article
import time
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from datetime import date

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Resume Ai", page_icon="resume ai", layout="wide")

# --- 2. LÓGICA DE AUTENTICAÇÃO ---
try:
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)
except FileNotFoundError:
    st.error("Arquivo de configuração 'config.yaml' não encontrado.")
    st.stop()

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator.login()

# --- 3. CONTROLE DE ACESSO E LÓGICA DA APLICAÇÃO ---
if st.session_state.get("authentication_status"):
    # ---- INÍCIO: Bloco de código para usuários logados ----

    # --- LÓGICA DE AUTORIZAÇÃO (VERIFICAÇÃO DE ASSINATURA) ---
    username = st.session_state.get("username")
    user_data = config['credentials']['usernames'].get(username, {})

    def verificar_validade_assinatura(details):
        """Verifica se a data de assinatura do usuário é válida."""
        if 'subscription_valid_until' not in details:
            return False
        try:
            data_validade = date.fromisoformat(str(details['subscription_valid_until']))
            return date.today() <= data_validade
        except (ValueError, TypeError):
            return False

    # Se a assinatura for válida, mostra o app. Senão, mostra mensagem de erro.
    if verificar_validade_assinatura(user_data):
        
        # Botão de Logout e mensagem de boas-vindas na barra lateral
        with st.sidebar:
            st.write(f'Bem-vindo(a), *{st.session_state["name"]}*')
            authenticator.logout('Logout', 'main')

        # --- FUNÇÕES DE BACKEND DO APP ---
        @st.cache_data(show_spinner=False)
        def analisar_texto_com_gemini(_texto):
            if not _texto or len(_texto) < 100:
                st.warning("O texto extraído é muito curto para uma análise significativa.")
                return None
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt_resumo_simples = f"Explique o conteúdo principal do seguinte texto como se eu tivesse 10 anos de idade (ELI5):\n\n{_texto}"
            prompt_analise_estruturada = f"Analise o seguinte texto e extraia os seguintes componentes em formato de tópicos:\n- A Ideia Principal\n- Os Argumentos ou Passos Apresentados\n- A Conclusão Principal\n\nTexto:\n{_texto}"
            prompt_gerar_perguntas = f"Baseado no texto a seguir, gere 3 perguntas inteligentes e críticas para testar o entendimento profundo do conteúdo:\n\nTexto:\n{_texto}"
            resultados = {}
            with st.spinner("Resume ai está trabalhando... (Isso pode levar um momento)"):
                resposta_resumo = model.generate_content(prompt_resumo_simples)
                resposta_analise = model.generate_content(prompt_analise_estruturada)
                resposta_perguntas = model.generate_content(prompt_gerar_perguntas)
                resultados["resumo_simples"] = resposta_resumo.text
                resultados["analise_estruturada"] = resposta_analise.text
                resultados["perguntas_criticas"] = resposta_perguntas.text
            return resultados

        # --- LÓGICA DAS PÁGINAS DO APP ---
        def pagina_principal():
            st.title("Precisa de ajuda? Eu resumo isso ai para você...")
            st.write("Resume Ai é uma plataforma de IA criada para analisar, resumir e conversar com qualquer conteúdo.")
            st.sidebar.title("Fonte do Conteúdo")
            fonte_selecionada = st.sidebar.radio(
                "Selecione o que você quer analisar:",
                ["Página Inicial", "Documento (PDF)", "Vídeo (YouTube)", "Artigo da Web"],
                key="fonte_selecao",
                index=0
            )
            texto_extraido = None
            if fonte_selecionada != "Vídeo (YouTube)":
                st.session_state.pop("video_url", None)
            if fonte_selecionada == "Documento (PDF)":
                st.subheader("Analisador de Documentos (PDF)")
                uploaded_file = st.file_uploader("Escolha um arquivo PDF", type="pdf", label_visibility="collapsed")
                if uploaded_file:
                    with st.spinner("Extraindo texto do PDF..."):
                        texto_bytes = uploaded_file.read()
                        with fitz.open(stream=BytesIO(texto_bytes), filetype="pdf") as doc:
                            texto_extraido = "".join(page.get_text() for page in doc)
            elif fonte_selecionada == "Vídeo (YouTube)":
                st.subheader("Analisador de Vídeos do YouTube")
                url_video = st.text_input("Cole a URL do vídeo do YouTube:")
                if url_video:
                    st.session_state.video_url = url_video 
                    with st.spinner("Buscando a transcrição do vídeo..."):
                        try:
                            video_id = None
                            if "v=" in url_video: video_id = url_video.split("v=")[1].split("&")[0]
                            elif "youtu.be/" in url_video: video_id = url_video.split("youtu.be/")[1].split("?")[0]
                            if video_id:
                                transcricao_lista = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en'])
                                texto_extraido = " ".join([item['text'] for item in transcricao_lista])
                            else: st.error("URL do YouTube inválida.")
                        except Exception as e: st.error(f"Não foi possível obter a transcrição. Erro: {e}")
            elif fonte_selecionada == "Artigo da Web":
                st.subheader("Analisador de Artigos da Web")
                url_artigo = st.text_input("Cole a URL do artigo:")
                if url_artigo:
                    with st.spinner("Lendo o artigo da web..."):
                        try:
                            article = Article(url_artigo)
                            article.download()
                            article.parse()
                            texto_extraido = article.text
                        except Exception as e: st.error(f"Não foi possível processar o artigo. Erro: {e}")
            if texto_extraido:
                st.session_state.texto_analisado = texto_extraido
                st.session_state.pagina_atual = "Resultados"
                st.rerun()

        def pagina_resultados_e_chat():
            st.title("Resultados da Análise")
            if st.sidebar.button("Analisar Outro Conteúdo", use_container_width=True):
                resetar_estado()
                st.rerun()
            if "analise_estatica" not in st.session_state:
                st.session_state.analise_estatica = analisar_texto_com_gemini(st.session_state.texto_analisado)
            if "chat_doc" not in st.session_state:
                prompt_inicial_chat = f"Você é um especialista no documento a seguir...\n\nO texto é:\n---\n{st.session_state.texto_analisado}\n---"
                model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=prompt_inicial_chat)
                st.session_state.chat_doc = model.start_chat(history=[])
                st.session_state.chat_messages = []
            lista_de_abas = ["Análise Inicial", "Conversar com o Documento"]
            if st.session_state.get("video_url"):
                lista_de_abas.append("Assistir ao Vídeo")
            tabs = st.tabs(lista_de_abas)
            with tabs[0]:
                st.header("Análise Automática do Conteúdo")
                resultados = st.session_state.get("analise_estatica")
                if resultados:
                    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Resumo Simples (ELI5)", "Análise Estruturada", "Perguntas Críticas"])
                    with sub_tab1: st.markdown(resultados["resumo_simples"])
                    with sub_tab2: st.markdown(resultados["analise_estruturada"])
                    with sub_tab3: st.markdown(resultados["perguntas_criticas"])
                else: st.error("A análise não pôde ser gerada.")
            with tabs[1]:
                st.header("Converse com seu Documento")
                for msg in st.session_state.chat_messages:
                    with st.chat_message(msg["role"]): st.markdown(msg["content"])
                if prompt := st.chat_input("Faça uma pergunta sobre o conteúdo..."):
                    st.session_state.chat_messages.append({"role": "user", "content": prompt})
                    with st.spinner("Analisando sua pergunta..."):
                        response = st.session_state.chat_doc.send_message(prompt).text
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    st.rerun()
            if len(tabs) > 2:
                with tabs[2]:
                    st.header("Player do Vídeo Original")
                    st.video(st.session_state.video_url)

        def resetar_estado():
            st.cache_data.clear()
            keys_to_delete = ["pagina_atual", "texto_analisado", "analise_estatica", "chat_doc", "chat_messages", "fonte_selecao", "video_url"]
            for key in keys_to_delete:
                if key in st.session_state:
                    del st.session_state[key]

        # --- CONTROLE DE NAVEGAÇÃO PRINCIPAL DO APP ---
        if "pagina_atual" not in st.session_state:
            st.session_state.pagina_atual = "Principal"
        if st.session_state.pagina_atual == "Principal":
            pagina_principal()
        elif st.session_state.pagina_atual == "Resultados":
            pagina_resultados_e_chat()

    else:
        # Se a assinatura expirou
        st.error("Sua assinatura expirou. Por favor, entre em contato para renovar seu acesso.")
        with st.sidebar:
            authenticator.logout('Logout', 'main')

elif st.session_state.get("authentication_status") is False:
    st.error('Usuário ou senha incorreta')
elif st.session_state.get("authentication_status") is None:
    st.warning('Por favor, insira seu usuário e senha para acessar o Resume Ai.')
  
