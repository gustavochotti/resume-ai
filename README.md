# Resume Ai

Resume Ai é uma plataforma de software como serviço (SaaS) desenvolvida em Python, que utiliza o poder da Inteligência Artificial Generativa para analisar, resumir e interagir com diversas fontes de conteúdo, como PDFs, vídeos do YouTube e artigos da web.

🔗 [Acesse a página de apresentação da plataforma](https://show-resume-ai.netlify.app)

🔗 [Acesse a aplicação online: Resume Ai - Live Demo](https://plataforma-resume-ai.streamlit.app)

---

## ✨ Funcionalidades Principais

O Resume Ai foi projetado para otimizar o processo de aprendizado e análise, oferecendo um conjunto robusto de funcionalidades:

### 🔍 Análise Multi-Fonte

Capacidade de processar e extrair texto de:

* Documentos PDF e TXT via upload.
* Vídeos do YouTube a partir de uma URL.
* Artigos da web a partir de um link.

### Inteligência Analítica Tripla

Para cada conteúdo, a IA gera automaticamente três tipos de análise para uma compreensão completa:

* **Resumo Simples (ELI5):** Uma explicação do tema em linguagem acessível.
* **Análise Estruturada:** Decomposição dos pontos-chave (Ideia Principal, Argumentos, Conclusão).
* **Perguntas Críticas:** Questões inteligentes que incentivam uma reflexão mais profunda.

### Chat Interativo com Documentos (RAG)

Uma interface de chat que permite ao usuário "conversar" com os documentos, fazendo perguntas específicas e recebendo respostas baseadas exclusivamente no texto-fonte.

### Análise de Múltiplos Documentos

Ferramenta poderosa onde o usuário pode fazer o upload de vários arquivos simultaneamente e usar o chat para obter insights e fazer comparações sobre o conteúdo combinado.

### Autenticação e Histórico

A plataforma possui um sistema de login seguro e futuramente terá a persistência de dados através de um banco de dados, permitindo que cada usuário acesse seu histórico de análises passadas.

---

## 🛠️ Stack de Tecnologias

Esta aplicação foi construída utilizando um conjunto de tecnologias modernas e robustas:

### Linguagem

* Python

### Framework Web

* Streamlit

### Inteligência Artificial & NLP

* Google Gemini API
* Retrieval-Augmented Generation (RAG)
* newspaper3k
* youtube-transcript-api
* PyMuPDF

### Banco de Dados e Autenticação

* Supabase (PostgreSQL)

### Testes Automatizados

* Pytest

### Deploy & Versionamento

* Streamlit Community Cloud
* Git & GitHub

