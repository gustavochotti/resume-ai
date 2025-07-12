import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import fitz  # PyMuPDF
from io import BytesIO
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from newspaper import Article
import time
from supabase import create_client, Client
from datetime import date, datetime, timedelta
import uuid

# --- MODELO DE IA ESCOLHIDO ---
ai_model = 'gemini-1.5-flash'

# --- 1. CONFIGURAÇÃO DA PÁGINA E CONEXÕES ---
st.set_page_config(page_title="Resume Ai", page_icon="💠", layout="wide")

@st.cache_resource
def init_connections():
    """Inicializa as conexões com Supabase e Gemini API."""
    try:
        url = st.secrets["SUPABASE_URL"]
        anon_key = st.secrets["SUPABASE_KEY"]
        service_key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
        supabase = create_client(url, anon_key)
        supabase_admin = create_client(url, service_key) if service_key else None
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return supabase, supabase_admin
    except Exception as e:
        st.error(f"Erro ao inicializar as conexões. Verifique suas chaves de API. Erro: {e}")
        st.stop()

supabase, supabase_admin = init_connections()

# --- 2. FUNÇÕES DE AUTENTICAÇÃO E PERFIL ---
def show_login_form():
    st.title("Bem-vindo ao Resume Ai")
    st.write("Faça login ou crie uma conta para continuar.")
    login_tab, signup_tab = st.tabs(["Login", "Criar Conta"])
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Senha", type="password")
            if st.form_submit_button("Login"):
                try:
                    session = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user_session = session.model_dump()
                    st.rerun()
                except Exception: st.error("Erro no login: Verifique seu e-mail e senha.")
    with signup_tab:
        with st.form("signup_form"):
            email = st.text_input("Email para cadastro")
            password = st.text_input("Crie uma senha", type="password")
            full_name = st.text_input("Nome Completo")
            if st.form_submit_button("Criar Conta"):
                if not supabase_admin:
                    st.error("A criação de novas contas está temporariamente desabilitada.")
                    return
                try:
                    cr = supabase_admin.auth.admin.create_user({"email": email, "password": password, "email_confirm": True, "user_metadata": {"full_name": full_name}})
                    user_id = cr.user.id
                    expiry = (date.today() + timedelta(days=7)).isoformat()
                    supabase_admin.table("profiles").upsert({"id": user_id, "full_name": full_name, "subscription_valid_until": expiry}, on_conflict="id").execute()
                    st.success("Conta criada! 7 dias gratuitos concedidos.")
                    st.info("Agora você pode fazer login na aba 'Login'.")
                except Exception as e: st.error(f"Erro ao criar conta: {e}")

def get_user_profile():
    if "user_session" in st.session_state:
        try:
            user_id = st.session_state.user_session['user']['id']
            response = supabase.table('profiles').select('*').eq('id', user_id).single().execute()
            return response.data
        except Exception: return None
    return None

def verificar_validade_assinatura(profile):
    if not profile: return False
    raw = profile.get('subscription_valid_until')
    if not raw: return False
    try:
        if isinstance(raw, str): valid_date = date.fromisoformat(raw)
        elif isinstance(raw, datetime): valid_date = raw.date()
        elif isinstance(raw, date): valid_date = raw
        else: return False
        return date.today() <= valid_date
    except (ValueError, TypeError): return False

# --- 3. CONTROLE DE FLUXO PRINCIPAL DA APLICAÇÃO ---

if "user_session" not in st.session_state or st.session_state.user_session is None:
    show_login_form()
else:
    user_profile = get_user_profile()

    if user_profile is None:
        st.error("Erro Crítico: Não foi possível carregar os dados do seu perfil.")
        with st.sidebar:
            st.write("⚠️ Erro de Perfil")
            if st.button("Logout"):
                supabase.auth.sign_out()
                for key in list(st.session_state.keys()): del st.session_state[key]
                st.rerun()

    elif verificar_validade_assinatura(user_profile):
        
        # --- FUNÇÕES DAS PÁGINAS (DEFINIDAS PRIMEIRO) ---
        
        def pagina_inicial():
            st.title(f"Bem-vindo(a) ao Resume Ai, *{user_profile.get('full_name', 'Usuário')}*!")
            st.subheader("O que você gostaria de fazer hoje?")
            
            # Acessa o dicionário PAGES, que agora estará definido
            cols = st.columns(len(PAGES))
            for i, (page_name, page_data) in enumerate(PAGES.items()):
                with cols[i]:
                    with st.container(border=True):
                        st.markdown(f"### {page_data['icon']} {page_name}")
                        st.markdown(page_data['desc'])
                        if st.button(f"Acessar {page_name}", key=f"nav_{page_name}", use_container_width=True):
                            st.session_state.current_page = page_name
                            st.rerun()

        if "analise_key" not in st.session_state:
            st.session_state.analise_key = str(uuid.uuid4())
            
        @st.cache_data(show_spinner=False, ttl=10)
        def analisar_texto_unico_com_gemini(_texto, _key):
            if not _texto or len(_texto) < 50:
                st.warning("O texto extraído é muito curto para uma análise significativa.")
                return None
            model = genai.GenerativeModel(ai_model)
            prompt_resumo = f"Explique o conteúdo principal do seguinte texto como se eu tivesse 10 anos de idade (ELI5):\n\n{_texto}"
            prompt_analise = f"Analise o seguinte texto e extraia em tópicos:\n- A Ideia Principal\n- Os Argumentos ou Passos Apresentados\n- A Conclusão Principal\n\nTexto:\n{_texto}"
            prompt_perguntas = f"Baseado no texto a seguir, gere 3 perguntas inteligentes e críticas:\n\nTexto:\n{_texto}"
            with st.spinner("Resume Ai está trabalhando na sua análise..."):
                r1 = model.generate_content(prompt_resumo)
                r2 = model.generate_content(prompt_analise)
                r3 = model.generate_content(prompt_perguntas)
            return {"resumo_simples": r1.text, "analise_estruturada": r2.text, "perguntas_criticas": r3.text}

        def pagina_analise_unica():
            st.title("Análise de Conteúdo Individual")
            st.info("Use esta seção para analisar um único documento, vídeo ou artigo da web.")
            st.header("Analisar Novo Conteúdo")
            fonte = st.radio("Selecione a fonte:", ["Documento (PDF ou TXT)", "Vídeo (YouTube)", "Artigo da Web"], key="fonte_unica", horizontal=True)
            texto_extraido, source_name = None, None
            if fonte == "Documento (PDF ou TXT)":
                f = st.file_uploader("Escolha um arquivo", type=["pdf", "txt"], key="upload_unico")
                if f:
                    source_name = f.name
                    with st.spinner(f"Extraindo texto de {f.name}..."):
                        if f.type == "application/pdf":
                            texto_extraido = "".join(p.get_text() for p in fitz.open(stream=f.read(), filetype="pdf"))
                        else:
                            texto_extraido = f.read().decode("utf-8")
            elif fonte == "Vídeo (YouTube)":
                # st.error("Funcionalidade de vídeo em manutenção. Por favor, use a opção de documento.", icon="⚠️")
                
                st.error("""
                Estamos enfrentando instabilidades para obter a transcrição diretamente do YouTube devido a questões de segurança da plataforma. Para garantir sua análise, recomendamos:
                1. Obtenha a transcrição em um site como o [YouTube Transcript](https://youtubetotranscript.com).
                2. Salve o texto como um arquivo PDF ou TXT.
                3. Selecione a opção **"Documento (PDF ou TXT)"** e faça o upload do arquivo.
                         
                Nossa IA fará a análise completa para você a partir do seu documento.
                
                Já estamos trabalhando em uma solução e estará disponível assim que possível. Pedimos desculpas pelo transtorno!
                """, icon="⚠️")

            else:
                url = st.text_input("Cole a URL do artigo:")
                if url:
                    source_name = url
                    with st.spinner("Lendo o artigo..."):
                        try:
                            art = Article(url); art.download(); art.parse()
                            texto_extraido = art.text
                        except Exception as e: st.error(f"Erro ao processar o artigo: {e}")
            if texto_extraido:
                st.success("Conteúdo extraído! Navegando para a página de resultados...")
                st.session_state.update({
                    "texto_analisado": texto_extraido, "source_name": source_name,
                    "source_type": fonte, "pagina_atual": "Resultados_Unico"
                })
                time.sleep(1)
                st.rerun()

        def pagina_resultados_e_chat():
            st.title(f"Resultados: {st.session_state.source_name}")
            if st.sidebar.button("‹ Voltar para o Início"):
                keys_to_clear = ["pagina_atual", "source_name", "source_type", "texto_analisado", "analise_estatica", "chat_doc_unico", "chat_messages_unico", "bloco_de_notas_content"]
                for key in keys_to_clear:
                    st.session_state.pop(key, None)
                st.session_state.current_page = "Página Inicial"
                st.session_state.analise_key = str(uuid.uuid4())
                st.rerun()

            if "analise_estatica" not in st.session_state:
                st.session_state.analise_estatica = analisar_texto_unico_com_gemini(st.session_state.texto_analisado, st.session_state.analise_key)
            if "chat_doc_unico" not in st.session_state:
                prompt_inicial_chat = f"Você é um especialista no seguinte texto:\n---\n{st.session_state.texto_analisado}\n---\nResponda perguntas baseadas exclusivamente neste conteúdo."
                model = genai.GenerativeModel(ai_model, system_instruction=prompt_inicial_chat)
                st.session_state.chat_doc_unico = model.start_chat(history=[])
                st.session_state.chat_messages_unico = []

            tab_analise, tab_chat, tab_notas = st.tabs(["📊 Análise Inicial", "💬 Conversar com o Documento", "📝 Bloco de Notas"])

            with tab_analise:
                resultados = st.session_state.get("analise_estatica")
                if resultados:
                    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Resumo Simples (ELI5)", "Análise Estruturada", "Perguntas Críticas"])
                    with sub_tab1: st.markdown(resultados["resumo_simples"])
                    with sub_tab2: st.markdown(resultados["analise_estruturada"])
                    with sub_tab3: st.markdown(resultados["perguntas_criticas"])
                else: st.error("A análise não pôde ser gerada.")
            
            with tab_chat:
                for msg in st.session_state.chat_messages_unico:
                    with st.chat_message(msg["role"]): st.markdown(msg["content"])
                if prompt := st.chat_input("Faça uma pergunta sobre o conteúdo..."):
                    st.session_state.chat_messages_unico.append({"role": "user", "content": prompt})
                    with st.spinner("Analisando sua pergunta..."):
                        response = st.session_state.chat_doc_unico.send_message(prompt).text
                        st.session_state.chat_messages_unico.append({"role": "assistant", "content": response})
                    st.rerun()

            with tab_notas:
                st.subheader("Suas Anotações sobre este Documento")
                if 'bloco_de_notas_content' not in st.session_state:
                    st.session_state.bloco_de_notas_content = ""
                default_title = f"Notas sobre {st.session_state.source_name}"
                note_title = st.text_input("Título da Nota", value=default_title)
                note_content = st.text_area("Escreva suas notas aqui.", key='bloco_de_notas_content', height=300)
                if st.button("Salvar Nota"):
                    if not note_title.strip() or not note_content.strip():
                        st.warning("Por favor, preencha o título e o conteúdo da nota.")
                    else:
                        try:
                            user_id = st.session_state.user_session['user']['id']
                            data = {"user_id": user_id, "title": note_title, "content": note_content}
                            supabase.table("user_notes").insert(data).execute()
                            st.success(f'Nota "{note_title}" salva com sucesso! Você pode vê-la na aba "Suas Notas".')
                        except Exception as e:
                            st.error(f"Ocorreu um erro ao salvar a nota: {e}")
        
        def pagina_chat_multiplos_arquivos():
            st.title("Chat Multi-Documentos")
            if "texto_multi_analise" not in st.session_state:
                st.info("Use esta seção para fazer upload de vários arquivos e conversar sobre o conteúdo combinado.")
                uploaded_files = st.file_uploader("Escolha os arquivos (PDF ou TXT)", type=["pdf", "txt"], accept_multiple_files=True, key="upload_multi")
                if uploaded_files:
                    if st.button("Processar Arquivos e Iniciar Chat"):
                        texto_combinado = ""
                        with st.spinner("Extraindo texto de todos os arquivos..."):
                            for file in uploaded_files:
                                try:
                                    texto_combinado += f"\n\n--- INÍCIO DO DOCUMENTO: {file.name} ---\n\n"
                                    if file.type == "application/pdf":
                                        texto_bytes = file.read()
                                        with fitz.open(stream=BytesIO(texto_bytes), filetype="pdf") as doc:
                                            texto_combinado += "".join(page.get_text() for page in doc)
                                    elif file.type == "text/plain":
                                        texto_combinado += file.read().decode("utf-8")
                                    texto_combinado += f"\n\n--- FIM DO DOCUMENTO: {file.name} ---\n\n"
                                except Exception as e:
                                    st.error(f"Erro ao processar o arquivo {file.name}: {e}")
                        st.session_state.texto_multi_analise = texto_combinado
                        st.success("Arquivos processados! Você já pode iniciar a conversa abaixo.")
                        st.rerun()
            if "texto_multi_analise" in st.session_state:
                if st.sidebar.button("‹ Voltar para o Início"):
                    keys_to_clear_multi = ["texto_multi_analise", "chat_multi_doc", "chat_multi_messages"]
                    for key in keys_to_clear_multi:
                        st.session_state.pop(key, None)
                    st.session_state.current_page = "Página Inicial"
                    st.rerun()
                if "chat_multi_doc" not in st.session_state:
                    prompt_inicial_chat = f"Você é um especialista que analisou múltiplos documentos..."
                    model = genai.GenerativeModel(ai_model, system_instruction=prompt_inicial_chat)
                    st.session_state.chat_multi_doc = model.start_chat(history=[])
                    st.session_state.chat_multi_messages = []
                st.subheader("Converse com seus Documentos")
                for msg in st.session_state.get("chat_multi_messages", []):
                    with st.chat_message(msg["role"]): st.markdown(msg["content"])
                if prompt := st.chat_input("Faça uma pergunta sobre o conteúdo combinado..."):
                    st.session_state.chat_multi_messages.append({"role": "user", "content": prompt})
                    with st.spinner("Analisando sua pergunta..."):
                        try:
                            response = st.session_state.chat_multi_doc.send_message(prompt).text
                            st.session_state.chat_multi_messages.append({"role": "assistant", "content": response})
                        except Exception as e:
                            st.error(f"Erro ao comunicar com a IA: {e}")
                    st.rerun()
        
        def pagina_suas_notas():
            st.title("Suas Notas Salvas")
            st.info("Aqui você pode ver, baixar e excluir suas anotações.")
            try:
                user_id = st.session_state.user_session['user']['id']
                response = supabase.table("user_notes").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
                notes = response.data
                if not notes:
                    st.write("Você ainda não tem nenhuma nota salva.")
                for note in notes:
                    with st.expander(f"**{note['title']}** - *Salvo em: {datetime.fromisoformat(note['created_at']).strftime('%d/%m/%Y %H:%M')}*"):
                        st.markdown(note['content'])
                        col1, col2 = st.columns([1, 0.2])
                        with col1:
                            st.download_button(label="Baixar como .txt", data=note['content'], file_name=f"{note['title']}.txt", mime="text/plain", key=f"download_{note['id']}")
                        with col2:
                            if st.button("Excluir", key=f"delete_{note['id']}", type="primary"):
                                try:
                                    supabase.table("user_notes").delete().eq("id", note['id']).execute()
                                    st.success(f'Nota "{note["title"]}" excluída.')
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao excluir a nota: {e}")
            except Exception as e:
                st.error(f"Não foi possível carregar suas notas: {e}")
        
        # --- CORREÇÃO: Dicionário PAGES movido para DEPOIS da definição das funções ---
        PAGES = {
            "Analisar Conteúdo": {
                "func": pagina_analise_unica,
                "icon": "📄",
                "desc": "Extraia insights de um único documento, vídeo ou artigo."
            },
            "Chat Multi-Documentos": {
                "func": pagina_chat_multiplos_arquivos,
                "icon": "📚",
                "desc": "Converse com vários arquivos ao mesmo tempo."
            },
            "Suas Notas": {
                "func": pagina_suas_notas,
                "icon": "📝",
                "desc": "Visualize, baixe e gerencie suas anotações salvas."
            }
        }
        
        # --- LÓGICA DE NAVEGAÇÃO E ROTEAMENTO ---

        if "current_page" not in st.session_state:
            st.session_state.current_page = "Página Inicial"

        PAGES_WITH_HOME = {"Página Inicial": {"func": pagina_inicial}, **PAGES}

        with st.sidebar:
            st.write(f'Bem-vindo(a), *{user_profile.get("full_name", "Usuário")}*')
            if st.button("Logout"):
                supabase.auth.sign_out()
                for key in list(st.session_state.keys()): del st.session_state[key]
                st.rerun()
            st.markdown("---")
            
            st.session_state.current_page = st.radio(
                "Menu",
                options=PAGES_WITH_HOME.keys(),
                key="sidebar_radio_nav",
                index=list(PAGES_WITH_HOME.keys()).index(st.session_state.current_page)
            )
        
        if st.session_state.get("pagina_atual") == "Resultados_Unico":
            pagina_resultados_e_chat()
        else:
            page_function = PAGES_WITH_HOME[st.session_state.current_page]["func"]
            page_function()

    else: # Assinatura expirada
        st.error("Sua assinatura expirou.")
        with st.sidebar:
            st.write(f'Olá, *{user_profile.get("full_name", "Usuário")}*')
            st.write("Status: 🔴 Assinatura Expirada")
            if st.button("Logout"):
                supabase.auth.sign_out()
                for key in list(st.session_state.keys()): del st.session_state[key]
                st.rerun()
