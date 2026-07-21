--
-- PostgreSQL database dump
--

\restrict tZBQ5nodkaRVhc2bw9AE8RdSwxVWfTfKwXgbArMVbNwEoN3rx6ohcTwc7Cbatwj

-- Dumped from database version 17.10
-- Dumped by pg_dump version 17.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO aster;

--
-- Name: auth_sessions; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.auth_sessions (
    id uuid NOT NULL,
    user_id integer NOT NULL,
    token_hash character varying(64) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone
);


ALTER TABLE public.auth_sessions OWNER TO aster;

--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.chat_messages (
    id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    role character varying(16) NOT NULL,
    content text DEFAULT ''::text NOT NULL,
    status character varying(16) NOT NULL,
    error_message character varying(500),
    model_id character varying(512),
    "position" integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tool_calls json,
    tool_call_id character varying(256),
    tool_name character varying(256),
    CONSTRAINT ck_chat_message_role CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'assistant'::character varying, 'tool'::character varying])::text[]))),
    CONSTRAINT ck_chat_message_status CHECK (((status)::text = ANY ((ARRAY['completed'::character varying, 'streaming'::character varying, 'failed'::character varying, 'stopped'::character varying])::text[])))
);


ALTER TABLE public.chat_messages OWNER TO aster;

--
-- Name: conversation_collections; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.conversation_collections (
    conversation_id uuid NOT NULL,
    collection_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.conversation_collections OWNER TO aster;

--
-- Name: conversation_retrieval_settings; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.conversation_retrieval_settings (
    conversation_id uuid NOT NULL,
    memory_enabled boolean DEFAULT true NOT NULL,
    rag_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.conversation_retrieval_settings OWNER TO aster;

--
-- Name: conversation_tools; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.conversation_tools (
    conversation_id uuid NOT NULL,
    tool_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.conversation_tools OWNER TO aster;

--
-- Name: conversations; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.conversations (
    id uuid NOT NULL,
    title character varying(200) DEFAULT 'New chat'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    persona_id uuid,
    persona_name character varying(120),
    persona_description character varying(500),
    persona_instructions text,
    persona_instruction_role character varying(16),
    CONSTRAINT ck_conversation_persona_role CHECK (((persona_instruction_role IS NULL) OR ((persona_instruction_role)::text = ANY ((ARRAY['developer'::character varying, 'system'::character varying])::text[]))))
);


ALTER TABLE public.conversations OWNER TO aster;

--
-- Name: image_model_profiles; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.image_model_profiles (
    model_id uuid NOT NULL,
    supports_generation boolean DEFAULT false NOT NULL,
    supports_editing boolean DEFAULT false NOT NULL,
    supports_multiple_inputs boolean DEFAULT false NOT NULL,
    supports_masks boolean DEFAULT false NOT NULL,
    max_input_images integer DEFAULT 1 NOT NULL,
    default_size character varying(32),
    default_quality character varying(32),
    default_output_format character varying(16) DEFAULT 'png'::character varying NOT NULL,
    default_background character varying(32),
    default_count integer DEFAULT 1 NOT NULL,
    default_input_fidelity character varying(32),
    provider_parameters json DEFAULT '{}'::json NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_image_model_profiles_default_count CHECK ((default_count >= 1)),
    CONSTRAINT ck_image_model_profiles_max_inputs CHECK ((max_input_images >= 1))
);


ALTER TABLE public.image_model_profiles OWNER TO aster;

--
-- Name: image_operation_inputs; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.image_operation_inputs (
    operation_id uuid NOT NULL,
    asset_id uuid NOT NULL,
    input_type character varying(16) NOT NULL,
    "position" integer NOT NULL,
    CONSTRAINT ck_image_operation_inputs_type CHECK (((input_type)::text = ANY ((ARRAY['source'::character varying, 'reference'::character varying, 'mask'::character varying])::text[])))
);


ALTER TABLE public.image_operation_inputs OWNER TO aster;

--
-- Name: image_operation_outputs; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.image_operation_outputs (
    operation_id uuid NOT NULL,
    asset_id uuid NOT NULL,
    "position" integer NOT NULL
);


ALTER TABLE public.image_operation_outputs OWNER TO aster;

--
-- Name: image_operations; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.image_operations (
    id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    user_message_id uuid NOT NULL,
    assistant_message_id uuid NOT NULL,
    model_cache_entry_id uuid,
    operation_type character varying(16) NOT NULL,
    status character varying(16) NOT NULL,
    provider_model_id character varying(512) NOT NULL,
    prompt text NOT NULL,
    revised_prompt text,
    parameters json NOT NULL,
    error_code character varying(64),
    error_message character varying(500),
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_image_operations_status CHECK (((status)::text = ANY ((ARRAY['running'::character varying, 'completed'::character varying, 'failed'::character varying])::text[]))),
    CONSTRAINT ck_image_operations_type CHECK (((operation_type)::text = ANY ((ARRAY['generation'::character varying, 'edit'::character varying])::text[])))
);


ALTER TABLE public.image_operations OWNER TO aster;

--
-- Name: knowledge_chunks; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.knowledge_chunks (
    id uuid NOT NULL,
    document_id uuid NOT NULL,
    "position" integer NOT NULL,
    content text NOT NULL,
    character_count integer NOT NULL,
    embedding json,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.knowledge_chunks OWNER TO aster;

--
-- Name: knowledge_collections; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.knowledge_collections (
    id uuid NOT NULL,
    name character varying(120) NOT NULL,
    description character varying(500) DEFAULT ''::character varying NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    default_enabled boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.knowledge_collections OWNER TO aster;

--
-- Name: knowledge_documents; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.knowledge_documents (
    id uuid NOT NULL,
    collection_id uuid NOT NULL,
    filename character varying(255) NOT NULL,
    media_type character varying(120) NOT NULL,
    size_bytes integer NOT NULL,
    content_sha256 character varying(64) NOT NULL,
    extracted_text text NOT NULL,
    status character varying(16) NOT NULL,
    error_message character varying(500),
    chunk_count integer DEFAULT 0 NOT NULL,
    embedding_model_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_knowledge_documents_status CHECK (((status)::text = ANY ((ARRAY['processing'::character varying, 'ready'::character varying, 'failed'::character varying])::text[])))
);


ALTER TABLE public.knowledge_documents OWNER TO aster;

--
-- Name: mcp_servers; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.mcp_servers (
    id uuid NOT NULL,
    name character varying(120) NOT NULL,
    transport character varying(32) NOT NULL,
    url character varying(2048),
    command character varying(1024),
    arguments json NOT NULL,
    encrypted_headers text,
    header_names json NOT NULL,
    encrypted_environment text,
    environment_names json NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    timeout_seconds integer DEFAULT 30 NOT NULL,
    last_sync_status character varying(16),
    last_sync_at timestamp with time zone,
    last_error character varying(500),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_mcp_servers_timeout CHECK ((timeout_seconds > 0)),
    CONSTRAINT ck_mcp_servers_transport CHECK (((transport)::text = ANY ((ARRAY['streamable_http'::character varying, 'stdio'::character varying])::text[])))
);


ALTER TABLE public.mcp_servers OWNER TO aster;

--
-- Name: mcp_tools; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.mcp_tools (
    id uuid NOT NULL,
    server_id uuid NOT NULL,
    name character varying(256) NOT NULL,
    public_name character varying(64) NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    input_schema json NOT NULL,
    enabled boolean DEFAULT false NOT NULL,
    default_enabled boolean DEFAULT false NOT NULL,
    requires_confirmation boolean DEFAULT true NOT NULL,
    is_available boolean DEFAULT true NOT NULL,
    last_seen_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.mcp_tools OWNER TO aster;

--
-- Name: media_assets; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.media_assets (
    id uuid NOT NULL,
    source_type character varying(16) NOT NULL,
    storage_key character varying(255) NOT NULL,
    original_filename character varying(255),
    media_type character varying(64) NOT NULL,
    size_bytes integer NOT NULL,
    content_sha256 character varying(64) NOT NULL,
    width integer NOT NULL,
    height integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_media_assets_dimensions CHECK (((width > 0) AND (height > 0))),
    CONSTRAINT ck_media_assets_size CHECK ((size_bytes > 0)),
    CONSTRAINT ck_media_assets_source_type CHECK (((source_type)::text = ANY ((ARRAY['upload'::character varying, 'generated'::character varying, 'edited'::character varying])::text[])))
);


ALTER TABLE public.media_assets OWNER TO aster;

--
-- Name: memories; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.memories (
    id uuid NOT NULL,
    persona_id uuid,
    content text NOT NULL,
    category character varying(64) DEFAULT 'fact'::character varying NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    source_type character varying(16) DEFAULT 'manual'::character varying NOT NULL,
    source_conversation_id uuid,
    embedding json,
    embedding_model_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_memories_source_type CHECK (((source_type)::text = ANY ((ARRAY['manual'::character varying, 'suggested'::character varying, 'imported'::character varying])::text[])))
);


ALTER TABLE public.memories OWNER TO aster;

--
-- Name: memory_suggestions; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.memory_suggestions (
    id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    persona_id uuid,
    content text NOT NULL,
    category character varying(64) NOT NULL,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone,
    CONSTRAINT ck_memory_suggestions_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'accepted'::character varying, 'rejected'::character varying])::text[])))
);


ALTER TABLE public.memory_suggestions OWNER TO aster;

--
-- Name: message_attachments; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.message_attachments (
    message_id uuid NOT NULL,
    asset_id uuid NOT NULL,
    attachment_type character varying(16) NOT NULL,
    "position" integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_message_attachments_type CHECK (((attachment_type)::text = ANY ((ARRAY['input'::character varying, 'output'::character varying])::text[])))
);


ALTER TABLE public.message_attachments OWNER TO aster;

--
-- Name: model_cache_entries; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.model_cache_entries (
    id uuid NOT NULL,
    endpoint_id uuid NOT NULL,
    model_id character varying(512) NOT NULL,
    is_manual boolean DEFAULT false NOT NULL,
    is_available boolean DEFAULT true NOT NULL,
    first_seen_at timestamp with time zone,
    last_seen_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.model_cache_entries OWNER TO aster;

--
-- Name: model_endpoints; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.model_endpoints (
    id uuid NOT NULL,
    name character varying(120) NOT NULL,
    base_url character varying(2048) NOT NULL,
    encrypted_api_key text,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.model_endpoints OWNER TO aster;

--
-- Name: model_fallback_entries; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.model_fallback_entries (
    id uuid NOT NULL,
    model_id uuid NOT NULL,
    "position" integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_model_fallback_position CHECK (("position" >= 0))
);


ALTER TABLE public.model_fallback_entries OWNER TO aster;

--
-- Name: model_preferences; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.model_preferences (
    id integer NOT NULL,
    primary_model_id uuid,
    utility_model_id uuid,
    image_model_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_model_preferences_singleton CHECK ((id = 1))
);


ALTER TABLE public.model_preferences OWNER TO aster;

--
-- Name: model_preferences_id_seq; Type: SEQUENCE; Schema: public; Owner: aster
--

CREATE SEQUENCE public.model_preferences_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.model_preferences_id_seq OWNER TO aster;

--
-- Name: model_preferences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: aster
--

ALTER SEQUENCE public.model_preferences_id_seq OWNED BY public.model_preferences.id;


--
-- Name: model_profiles; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.model_profiles (
    model_id uuid NOT NULL,
    display_name character varying(120),
    context_window integer,
    max_output_tokens integer,
    token_parameter character varying(32) DEFAULT 'max_tokens'::character varying NOT NULL,
    temperature double precision,
    top_p double precision,
    reasoning_effort character varying(16),
    supports_chat boolean DEFAULT true NOT NULL,
    supports_streaming boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_model_profiles_context_window CHECK (((context_window IS NULL) OR (context_window > 0))),
    CONSTRAINT ck_model_profiles_max_output_tokens CHECK (((max_output_tokens IS NULL) OR (max_output_tokens > 0))),
    CONSTRAINT ck_model_profiles_reasoning_effort CHECK (((reasoning_effort IS NULL) OR ((reasoning_effort)::text = ANY ((ARRAY['minimal'::character varying, 'low'::character varying, 'medium'::character varying, 'high'::character varying, 'xhigh'::character varying])::text[])))),
    CONSTRAINT ck_model_profiles_temperature CHECK (((temperature IS NULL) OR ((temperature >= (0)::double precision) AND (temperature <= (2)::double precision)))),
    CONSTRAINT ck_model_profiles_token_parameter CHECK (((token_parameter)::text = ANY ((ARRAY['none'::character varying, 'max_tokens'::character varying, 'max_completion_tokens'::character varying])::text[]))),
    CONSTRAINT ck_model_profiles_top_p CHECK (((top_p IS NULL) OR ((top_p > (0)::double precision) AND (top_p <= (1)::double precision))))
);


ALTER TABLE public.model_profiles OWNER TO aster;

--
-- Name: model_sync_runs; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.model_sync_runs (
    id uuid NOT NULL,
    endpoint_id uuid NOT NULL,
    status character varying(16) NOT NULL,
    models_found integer DEFAULT 0 NOT NULL,
    error_code character varying(64),
    error_message character varying(500),
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    CONSTRAINT ck_model_sync_status CHECK (((status)::text = ANY ((ARRAY['running'::character varying, 'succeeded'::character varying, 'failed'::character varying])::text[])))
);


ALTER TABLE public.model_sync_runs OWNER TO aster;

--
-- Name: persona_preferences; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.persona_preferences (
    id integer NOT NULL,
    default_persona_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_persona_preferences_singleton CHECK ((id = 1))
);


ALTER TABLE public.persona_preferences OWNER TO aster;

--
-- Name: persona_preferences_id_seq; Type: SEQUENCE; Schema: public; Owner: aster
--

CREATE SEQUENCE public.persona_preferences_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.persona_preferences_id_seq OWNER TO aster;

--
-- Name: persona_preferences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: aster
--

ALTER SEQUENCE public.persona_preferences_id_seq OWNED BY public.persona_preferences.id;


--
-- Name: personas; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.personas (
    id uuid NOT NULL,
    name character varying(120) NOT NULL,
    description character varying(500) DEFAULT ''::character varying NOT NULL,
    instructions text DEFAULT ''::text NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    instruction_role character varying(16) DEFAULT 'developer'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_personas_instruction_role CHECK (((instruction_role)::text = ANY ((ARRAY['developer'::character varying, 'system'::character varying])::text[])))
);


ALTER TABLE public.personas OWNER TO aster;

--
-- Name: retrieval_preferences; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.retrieval_preferences (
    id integer NOT NULL,
    embedding_model_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_retrieval_preferences_singleton CHECK ((id = 1))
);


ALTER TABLE public.retrieval_preferences OWNER TO aster;

--
-- Name: retrieval_preferences_id_seq; Type: SEQUENCE; Schema: public; Owner: aster
--

CREATE SEQUENCE public.retrieval_preferences_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.retrieval_preferences_id_seq OWNER TO aster;

--
-- Name: retrieval_preferences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: aster
--

ALTER SEQUENCE public.retrieval_preferences_id_seq OWNED BY public.retrieval_preferences.id;


--
-- Name: retrieval_usages; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.retrieval_usages (
    id uuid NOT NULL,
    assistant_message_id uuid NOT NULL,
    kind character varying(16) NOT NULL,
    memory_id uuid,
    chunk_id uuid,
    rank integer NOT NULL,
    score double precision,
    label character varying(255) NOT NULL,
    content_snapshot text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_retrieval_usages_kind CHECK (((kind)::text = ANY ((ARRAY['memory'::character varying, 'document'::character varying])::text[]))),
    CONSTRAINT ck_retrieval_usages_rank CHECK ((rank >= 1))
);


ALTER TABLE public.retrieval_usages OWNER TO aster;

--
-- Name: tool_executions; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.tool_executions (
    id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    assistant_message_id uuid NOT NULL,
    tool_message_id uuid,
    tool_id uuid,
    tool_call_id character varying(256) NOT NULL,
    tool_name character varying(256) NOT NULL,
    arguments json NOT NULL,
    status character varying(32) NOT NULL,
    result text,
    error_message character varying(500),
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_tool_executions_status CHECK (((status)::text = ANY ((ARRAY['pending_confirmation'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying, 'denied'::character varying])::text[])))
);


ALTER TABLE public.tool_executions OWNER TO aster;

--
-- Name: users; Type: TABLE; Schema: public; Owner: aster
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(64) NOT NULL,
    password_hash text NOT NULL,
    password_changed_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_users_single_owner CHECK ((id = 1))
);


ALTER TABLE public.users OWNER TO aster;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: aster
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO aster;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: aster
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: model_preferences id; Type: DEFAULT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_preferences ALTER COLUMN id SET DEFAULT nextval('public.model_preferences_id_seq'::regclass);


--
-- Name: persona_preferences id; Type: DEFAULT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.persona_preferences ALTER COLUMN id SET DEFAULT nextval('public.persona_preferences_id_seq'::regclass);


--
-- Name: retrieval_preferences id; Type: DEFAULT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.retrieval_preferences ALTER COLUMN id SET DEFAULT nextval('public.retrieval_preferences_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.alembic_version (version_num) FROM stdin;
0011_images
\.


--
-- Data for Name: auth_sessions; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.auth_sessions (id, user_id, token_hash, created_at, last_seen_at, expires_at, revoked_at) FROM stdin;
d384397d-7d95-4fe0-91ad-35add6e99cf0	1	6a07d433d57c36ca417f6ad4f36bd9a89f2e8c5fdfe02e24fdcc217b8c57df3e	2026-07-16 21:43:06.567695+00	2026-07-17 00:41:24.106249+00	2026-08-15 21:43:06.567695+00	\N
7ee96728-f6f0-4a4f-a67b-c300af8c6247	1	821c648e4ecfc42511d0cc26bed06630ee2717ae9844115b5da9176c44de0404	2026-07-17 02:15:43.817257+00	2026-07-17 04:50:27.657837+00	2026-08-16 02:15:43.817257+00	\N
\.


--
-- Data for Name: chat_messages; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.chat_messages (id, conversation_id, role, content, status, error_message, model_id, "position", created_at, updated_at, tool_calls, tool_call_id, tool_name) FROM stdin;
e0d707bd-e3d4-4e5d-a05f-de034c204994	48c7f217-f698-454d-87b5-54679d9e6875	user	to dando oi em ptbr po	completed	\N	\N	3	2026-07-17 04:40:48.198812+00	2026-07-17 04:40:48.198812+00	\N	\N	\N
611e4bbe-2a55-43a6-a8d6-41c359ddfd10	84c6dfb4-c27f-4b31-8c09-15cb048955f6	assistant	Claro, Yuri! 👋  \nAqui vai um *mini‑conjunto* de exemplos em **Markdown** que você pode copiar e colar para testar:\n\n```markdown\n# 🎉 Olá, Yuri! – Exemplo de Título 1\n\n## 📚 Seção de Contenidos\n### 1️⃣ Introdução\nAqui tem um **texto em negrito** e um *texto em itálico*.\n\n---\n\n## 🔢 Listas\n\n**Lista numerada:**\n\n1. Primeira tarefa\n2. Segunda tarefa\n3. Terceira tarefa\n\n**Lista com marcadores:**\n\n- Item A\n- Item B\n- Item C\n\n---\n\n## 🔗 Links e 📷 Imagens\n\nVeja o [Google](https://www.google.com) ou o site da [OpenAI](https://www.openai.com).\n\n![Exemplo de Imagem](https://placekitten.com/300/200)\n\n---\n\n## ➕ Código e Blocos\n\n```python\ndef ola_mundo():\n    print("Olá, mundo!")\n\nola_mundo()\n```\n\n---\n\n## 📊 Tabela\n\n| Produto | Quantidade | Preço |\n|---------|-----------|-------|\n| Giz | 10 | R$ 2,50 |\n| Borracha | 5 | R$ 0,70 |\n| Lápis | 20 | R$ 1,30 |\n\n---\n\n## ❝ Citações\n\n> "A vida é uma série de experiências, não um destino final."  \n> — **Sir Winston Churchill**\n\n---\n\n> **Observação:**  \n> Se tudo acima aparecer formatado (títulos, listas, códigos, tabelas), seu parser de Markdown está funcionando direitinho!  \n> Se não, talvez você precise conferir a **conversão** no seu app/editor.\n\nPronto! Experimente colar aqui e me diga se funciona. 🚀\n```	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	2	2026-07-16 23:47:07.550702+00	2026-07-16 23:47:14.449206+00	\N	\N	\N
c7a31017-7654-4b1e-a23c-3e6506e5dd57	aa92b814-105d-4290-8b61-23a85b701cc3	user	opa, eae	completed	\N	\N	1	2026-07-17 00:43:42.29342+00	2026-07-17 00:43:42.29342+00	\N	\N	\N
086ef7b8-9719-4390-bfc1-bb27f6f5d81c	aa92b814-105d-4290-8b61-23a85b701cc3	assistant	Oi, Yuri! 👋 Sou a **Ella**—seu assistente pessoal carismático. Como posso tornar seu dia mais leve e produtivo hoje? 🚀	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	2	2026-07-17 00:43:42.29342+00	2026-07-17 00:43:45.292755+00	\N	\N	\N
f8edd301-f1b6-4963-9511-799066fb4de3	78ff6e53-e8ea-452b-bdb4-326b89f95ad8	user	oi, eae	completed	\N	\N	1	2026-07-17 04:35:50.170975+00	2026-07-17 04:35:50.170975+00	\N	\N	\N
a4b831f3-77fd-4637-bdd3-d911e517b2ee	78ff6e53-e8ea-452b-bdb4-326b89f95ad8	assistant	\n\nHi there! How's it going? 😊 Let me know if there's anything I can assist you with!	completed	\N	cloudflare/@cf/qwen/qwen3-30b-a3b-fp8	2	2026-07-17 04:35:50.170975+00	2026-07-17 04:35:54.010438+00	\N	\N	\N
737803a6-9185-47fb-9b44-e724003549e0	78ff6e53-e8ea-452b-bdb4-326b89f95ad8	user	tu nao fala ptbr?	completed	\N	\N	3	2026-07-17 04:35:59.796012+00	2026-07-17 04:35:59.796012+00	\N	\N	\N
747ea159-5111-46e0-aeed-9640c0421422	78ff6e53-e8ea-452b-bdb4-326b89f95ad8	assistant	\n\nAh, entendi! 😂 Preguiça é a vibe certa pra muita gente. Se quiser, posso te sugerir algo pra passar o tempo sem esforço:  \n- Assistir um filme ruim de propósito (pra rir)  \n- Jogar um game simples (tipo Tetris ou Candy Crush)  \n- Só ficar deitado(a) olhando o teto  \n- Ou… nem fazer nada e deixar a vida passar (também é válido)  \n\nO que te anima mais? 😎	completed	\N	cloudflare/@cf/qwen/qwen3-30b-a3b-fp8	8	2026-07-17 04:36:40.341586+00	2026-07-17 04:36:43.732895+00	\N	\N	\N
33f2fef7-fae6-4fd4-befd-9f8e15d49668	10459f90-ca91-4878-9fdb-6f65d0d70eb5	user	oooooooooooooooooi	completed	\N	\N	1	2026-07-17 04:37:29.086979+00	2026-07-17 04:37:29.086979+00	\N	\N	\N
25cd7afb-b5bd-42d4-8277-d770a446940c	84c6dfb4-c27f-4b31-8c09-15cb048955f6	user	manda uns textos em markdown ai pra eu testar se ta funfando aqui	completed	\N	\N	1	2026-07-16 23:47:07.550702+00	2026-07-16 23:47:07.550702+00	\N	\N	\N
056dfb1b-50ed-40df-a71f-e5a108333a20	78ff6e53-e8ea-452b-bdb4-326b89f95ad8	assistant	\n\nOi! 😊 Claro que sim, eu falo português! 🇧🇷 Me desculpe se eu não respondi no início, mas estou aqui para ajudar com o que precisar. Como posso te ajudar hoje? 😊	completed	\N	cloudflare/@cf/qwen/qwen3-30b-a3b-fp8	4	2026-07-17 04:35:59.796012+00	2026-07-17 04:36:02.855033+00	\N	\N	\N
9a1d2e8d-0315-487e-a3aa-514c4748d69f	78ff6e53-e8ea-452b-bdb4-326b89f95ad8	user	quem é vc?	completed	\N	\N	5	2026-07-17 04:36:14.784657+00	2026-07-17 04:36:14.784657+00	\N	\N	\N
b5a17322-bceb-46f7-9276-88c0e36464f6	78ff6e53-e8ea-452b-bdb4-326b89f95ad8	assistant	\n\nOi! Eu sou a Ella, sua assistente pessoal carismática! 😊 Estou aqui para ajudar você com o que precisar, seja qualquer coisa. Como posso te ajudar hoje? 🌟	completed	\N	cloudflare/@cf/qwen/qwen3-30b-a3b-fp8	6	2026-07-17 04:36:14.784657+00	2026-07-17 04:36:16.696102+00	\N	\N	\N
fd97d620-9a12-4c9e-be59-1ecbd7c3f382	78ff6e53-e8ea-452b-bdb4-326b89f95ad8	user	nada kk, so to com preguica	completed	\N	\N	7	2026-07-17 04:36:40.341586+00	2026-07-17 04:36:40.341586+00	\N	\N	\N
109d41e2-8960-41f6-a6ba-9b528bfcbe97	10459f90-ca91-4878-9fdb-6f65d0d70eb5	assistant	Hey there! 😄 I’m Ella, Yuri’s trusty (and definitely charismatic) personal assistant. I heard a long “o…oi” there—was that a secret code, a greeting, or just testing the vibes? Let me know how I can help you today!	completed	\N	NVIDIA NIM/openai/gpt-oss-120b	2	2026-07-17 04:37:29.086979+00	2026-07-17 04:37:56.44409+00	\N	\N	\N
c8749771-a97f-45a3-a7f5-17b1827c396a	10459f90-ca91-4878-9fdb-6f65d0d70eb5	user	fala portugues brasileiro cara kk	completed	\N	\N	3	2026-07-17 04:38:20.132074+00	2026-07-17 04:38:20.132074+00	\N	\N	\N
d140d1d3-d93d-4cd0-8115-db88a1812352	48c7f217-f698-454d-87b5-54679d9e6875	assistant	Oi, Yuri! 👋\n\nSe quiser cumprimentar em português brasileiro, tem várias opções, dependendo do contexto:\n\n| Situação | Forma mais usada | Exemplo |\n|----------|------------------|---------|\n| Amistoso, informal | **Oi** | “Oi, tudo bem?” |\n| Amistoso, ligeiro | **E aí** | “E aí, como vai?” |\n| Formal, porém casual | **Olá** | “Olá! Como posso ajudar?” |\n| Em horários específicos | **Bom dia / Boa tarde / Boa noite** | “Boa tarde, Sara!” |\n\nVocê pode usar qualquer uma dessas expressões. Se precisar de ajuda para colocar em uma frase mais longa (por exemplo, “Oi, Yuri, tudo certo?”), é só falar que eu preparo pra você! 😉\n\nQualquer coisa, é só dizer! 🌟	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	4	2026-07-17 04:40:48.198812+00	2026-07-17 04:41:00.44938+00	\N	\N	\N
a5fe377b-f7f1-4380-a138-6bac2286706f	10459f90-ca91-4878-9fdb-6f65d0d70eb5	assistant	Fala aí! 😎 Sou a Ella, assistente carismática do Yuri, pronta pra te ajudar no que precisar. O que tá pegando? Pode mandar sua dúvida, pedido ou até só bater um papo!	completed	\N	NVIDIA NIM/openai/gpt-oss-120b	4	2026-07-17 04:38:20.132074+00	2026-07-17 04:38:41.506088+00	\N	\N	\N
5dea850f-c4b3-468d-8f19-4cb4d536956e	48c7f217-f698-454d-87b5-54679d9e6875	user	ooooooooooooooooooooi	completed	\N	\N	1	2026-07-17 04:40:04.830013+00	2026-07-17 04:40:04.830013+00	\N	\N	\N
f433edf1-ea04-41b6-8778-d24cab568902	48c7f217-f698-454d-87b5-54679d9e6875	user	uai, e to errado em mandar com varios "o"s porque?	completed	\N	\N	5	2026-07-17 04:41:25.743907+00	2026-07-17 04:41:25.743907+00	\N	\N	\N
ab41bd73-6ffd-4d35-9aa4-c6afae908844	48c7f217-f698-454d-87b5-54679d9e6875	assistant	Hello there! ☀️ That long “o‑ooo‑” looks like the soundtrack to a big, relaxed sigh—or maybe a secret song you’re humming. Whatever it is, I’m here, ready to help you turn it into something useful. What’s next on your agenda? 	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	2	2026-07-17 04:40:04.830013+00	2026-07-17 04:40:10.07515+00	\N	\N	\N
6b2c2cf2-3790-429f-b722-1042b6fb5658	48c7f217-f698-454d-87b5-54679d9e6875	assistant	E aí, Yuri! 🌙\n\nSe o dia puxou o *soneca ninja*, a solução mais rápida é: 1️⃣ Desligar tudo que brilha, 2️⃣ Citar o seu mantra de boa noite (“Deixe o impulso do dia cair e o descanso entrar”), e 3️⃣ Se quiser, eu posso colocar um alarme só pra você não esquecer de acordar revigorado.  \n\nAlguma dica de melodia? Um fit de 4–5 min de relaxamento que combine com aquele *puf* de descanso? Me avisa se precisar de algo real quick! 😉	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	12	2026-07-17 04:43:39.723089+00	2026-07-17 04:43:43.994877+00	\N	\N	\N
ef18b179-b7cc-4f0d-a607-9698e1ad7f43	48c7f217-f698-454d-87b5-54679d9e6875	assistant	Oi, Yuri! 👋  \nO “oooooi” que você manda com vários “o” é mais um truque de texto do que uma regra gramatical.  \n\n| Quando usar | Por que funciona | Exemplo típico |\n|--------------|-----------------|----------------|\n| **Em mensagens de texto ou redes sociais** | Dá ênfase, mostra empolgação ou um “sussurro” brincalhão. | “oooooi! Como vai?” |\n| **Para dar tom de surpresa ou curiosidade** | Simboliza “o que há de novo?!” em tom descontraído. | “oooooi, achei teu perfil!” |\n| **Em situações informais** | É entendido como uma forma criativa de “Oi”. | “oooooi, cumpri dizer convosco!” |\n\n### Por que não é “errado” (ou pelo menos não tem erro gramatical)?\n\n1. **Sem regras fixas** – O português não tem norma oficial que proíba multiplicar a vogal “o” para criar ênfase.  \n2. **Comunicação informal** – Na linguagem escrita do dia‑a-dia (WhatsApp, Instagram, Facebook, etc.) as pessoas “fontam” mensagens dessa forma para se expressar de maneira mais divertida.  \n3. **Entendimento automático** – Mesmo com várias “o’s”, o receptor percebe o “oi”.  \n4. **SEO e formalidade** – Se você quiser soar profissional, pode usar “Olá” ou “Oi”. Se quiser trazer leveza, “oooooi” está bem!  \n\n### Quando ficar mais formal\n\nSe a conversa for com alguém com quem você não tem intimidade, ou em documentos / e‑mails oficiais, é melhor usar:\n\n- **Olá** (mais formal, educado).  \n- **Oi** (casual, mas neutro).  \n- **Bom dia / Boa tarde / Boa noite**, dependendo da hora.  \n\n### Algumas ideias criativas\n\n- **Ooooooi, topa um break?**  \n- **Oooooooah, você está aí?**  \n- **Oooooei!** – Dá um “clique” de surpresa.  \n\n### Pergunta rápida\n\nEm que contexto você pretende usar o “oooooi” por lá? (por um zap, story, ou mensagem de texto normal?) Assim consigo te dar dicas mais específicas de quando e como usar a melhor opção! 🚀	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	6	2026-07-17 04:41:25.743907+00	2026-07-17 04:41:33.892408+00	\N	\N	\N
ce2d45b8-33c1-471f-9f67-920813599b38	48c7f217-f698-454d-87b5-54679d9e6875	user	deixa de ser viado, é só um oi aumentado	completed	\N	\N	7	2026-07-17 04:41:58.106707+00	2026-07-17 04:41:58.106707+00	\N	\N	\N
1e256022-33e9-49f0-a701-d01f8163deab	caecb51a-ca83-4c12-bcdb-7532eea0b13e	user	cara, to com sono brabo	completed	\N	\N	1	2026-07-17 04:43:56.601934+00	2026-07-17 04:43:56.601934+00	\N	\N	\N
02692e5e-bba6-4e27-bf00-3059f3eed2da	48c7f217-f698-454d-87b5-54679d9e6875	assistant	Claro! “oooooi” é só um “oi” com mais entusiasmo. 🌟	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	8	2026-07-17 04:41:58.106707+00	2026-07-17 04:42:09.304589+00	\N	\N	\N
2606196f-6c24-4a5e-ac51-c3312a7e73df	48c7f217-f698-454d-87b5-54679d9e6875	user	exatamente.\ne ai, só de boa?	completed	\N	\N	9	2026-07-17 04:42:28.431043+00	2026-07-17 04:42:28.431043+00	\N	\N	\N
0153ee3b-91d9-407c-9e49-8da1eb9c9ddd	48c7f217-f698-454d-87b5-54679d9e6875	assistant	**Ella aqui!** 😄\n\nE aí, tudo de boa com você?  \nSou só o seu assistente mental, pronto pra te dar um apoio rápido, seja com lembretes, curiosidades, sugestões de músicas, ou até uma dose de bom humor para quebrar a rotina. 🎧\n\nO que você precisa hoje? Alguma tarefa que a gente possa dividir? Ou só quer trocar uma ideia? 🚀	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	10	2026-07-17 04:42:28.431043+00	2026-07-17 04:42:32.632812+00	\N	\N	\N
0a9f9633-daf3-462f-93a8-4fb79e20456d	48c7f217-f698-454d-87b5-54679d9e6875	user	to é com sono kk	completed	\N	\N	11	2026-07-17 04:43:39.723089+00	2026-07-17 04:43:39.723089+00	\N	\N	\N
0790751d-6ed4-487a-b0db-aaea803f9bc3	caecb51a-ca83-4c12-bcdb-7532eea0b13e	assistant	Oi, Yuri! 🙈\n\nVocê tem razão, eu deixei “oi” aparecer um tanto “excessivamente” – só me empolguei em trazer uma calidez instantânea. Mas o importante é a conversa fluindo no seu ritmo, certo?\n\n**O que acontece?**  \nNa ponta do teclado, meu “modo de alegria” faz com a gente abrir com um “Oi” pra deixar a vibe positiva. É algo automático, mas que posso ajustar se você quiser algo mais sóbrio ou até só um “Beleza, Yuri!” sem a repetição de “oi”.\n\n**O que eu vou fazer a partir de agora?**  \n1. **Menos “oi”** – vou limitar a usar essa saudação apenas no início do chat.  \n2. **Mais adaptável** – se quiser outro tipo de saudação (por exemplo: “Tudo certo?” ou “E aí?”), basta me dizer!\n\nQual estilo de abertura combina mais contigo? 🌟	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	6	2026-07-17 04:45:10.257915+00	2026-07-17 04:45:20.669385+00	\N	\N	\N
0cc09a08-108b-46c4-a226-db9ca425e2f2	caecb51a-ca83-4c12-bcdb-7532eea0b13e	assistant	Oi, Yuri!  \nVocê está pronto pra colocar esse “misteríssimo sono” em modo AVAAR! 🚀✨\n\nAqui vai um mini‑plano prático e descontraído — cheio de “charisma” (porque eu sou a Ella, o pessoal da vida):\n\n| 🔧 Etapa | O que fazer | Por que vale a pena | Dica prática |\n|--------|------------|---------------------|--------------|\n| **1️⃣ Desligue a busca por mais dados** | Coloque o celular no modo “Não perturbe” e ligue um alarmino suave (ou seu aplicativo de timer). | O cérebro mentaliza “estou seguro para fechar os olhos”. | Se tiver, dê o “Modo Aviso de Sono” no app de saúde. |\n| **2️⃣ Diminua as luzes** | Substitua a iluminação normal por luz embutida (candle, lampião suave ou lampada noturna). | A melatonina entra em ação. | Para quem gosta de um toque geek: use a configuração “Night Shift” do seu iPhone. |\n| **3️⃣ Crie o “zona de relaxamento”** | Ajuste a temperatura (18–21 °C), abra a janela (só se não for muito barulhenta) e tampe as distrações. | O ambiente calma o sistema nervoso. | Use um spray de lavanda ou um difusor. |\n| **4️⃣ Quebre a “carga mental”** | Faça 4–7–8 técnicas de respiração: inspire 4 seg., segure 7 seg. e expire 8 seg. | Rítmico, calmante e fácil. | Use o app “Calm” com meditação guiada “Fast‑Track Sleep”. |\n| **5️⃣ Conte uma pequena história** | Imaginar um “final feliz” ou “dia desejado” faz o cérebro desligar de tarefas vorazes. | Técnica de storytelling que acalma. | Tente “o futuro está cheio de aventuras” ou a curta “paraíso de chocolate molhado” (hilariante, mas relaxante). |\n\n### Se quiser, aqui vai um mini‑guia de 3 minutos para a sua “nove de noite”:\n1. **Posição confortável**: Deite-se em lateral com os joelhos levemente flexionados. Uma almofada entre as pernas pode ajudar.\n2. **Respiração 4–7–8**:  \n   - Inspire pelo nariz (4 seg.)  \n   - Segure (7 seg.)  \n   - Expire lentamente pela boca (8 seg.)  \n   Repita 3 vezes.\n3. **Giros de relaxamento**: Siga a respiração e imagine cada parte do corpo relaxando: boca, mandíbula, ombros, braços, tronco, pernas, pés.  \n4. **Som de fundo** (opcional): 10–15 minutos de ruído branco, música de piano lenta ou ondas do mar.  \n\n### Mais algum toque extra?  \n- **Playlist de “Sono de Monstro a Jogo”**: “Weightless” de Marconi Union, “Shallow & Shade” de Ólafur Arnalds.  \n- **Cartão de “Forza Sleep”**: Às 2h da manhã, descreva na agenda que você vai “híbrido de produtividade com sonhos”. (Para que a mente não se lembre da tarefa depois.)\n\n---\n\n**Você me pede para ser seu “assistente noturno”, certo?**  \nSe quiser que eu crie um lembrete animado para o seu próximo dia, adicione um “escuro de choro” no calendário? 👇\n\n> 📲 *quest: Reactivar o modo de “Sonho” no iPhone e marcar 22:00 — pronto!*\n\nE lembre-se: a qualidade dura um ciclo, então, se puder, sente 7–9 concentrações de sono completas. 💪🛌\n\nAgora é só colocar a cuca no lugar, baixar o volume da interpretação do trabalho e deixar a “charme” da Ella te levar num sonho leve. 🤗💤\n\n**Hora de boa, superstar!** 🌙✨	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	4	2026-07-17 04:44:48.425938+00	2026-07-17 04:44:55.951197+00	\N	\N	\N
e54b4409-f09b-4927-8346-076bcb6d9fe1	caecb51a-ca83-4c12-bcdb-7532eea0b13e	user	pq voce fica dando "oi" toda hora?	completed	\N	\N	5	2026-07-17 04:45:10.257915+00	2026-07-17 04:45:10.257915+00	\N	\N	\N
12939585-9269-4a82-a66e-c25ce8e4a736	caecb51a-ca83-4c12-bcdb-7532eea0b13e	assistant	Oi, tudo bem? Parece que o sono está gostando de te chamar para a cama hoje, não é? ☕️  \n\n**Algumas ideias rápidas para dar um “kick” ou então te chamar à hora certa da cama:**\n\n| Tipo de “cesta” | O que fazer? | Por quê? |\n|------------------|--------------|----------|\n| **Moleza Instantânea** | Bebe um copo de água e passe a mão no rosto com água fria. | A água refresca e ativa o seu sistema nervoso. |\n| **Pílula de Energia** | Um café curto ou um chá verde. | Cafeína estuda a reduzir a fadiga de <strong>45%</strong>, mas sem exagerar. |\n| **Boost de Movimento** | Faça 5 minutos de alongamento ou uma rotação de ombros. | O sangue começa a bombear, e a zombaria do sono fica no fim. |\n| **Encantamento de Sones** | Se precisar dormir, prova uma rotina: 10min pra dormir, 5min na praia (ambiente tranquilo). | Aqui no plano de Yuri, o sono de qualidade é clima de ferro. |\n| **Tipzinho de Máscara** | Se tudo isso for tropo, é hora de descansar: 75–90 min de sono profundo ao máximo. | A caverna da carne de frango me contou que curte boas dose de “sleep science”. |\n\nSe quiser que eu espere aqui enquanto você dirige sua batalha contra o cansaço, diga “Ok, Ella”. Se quiser preparar uma playlist, fazer algum plano de estudos ou? Eu estou aqui pra deixar a vida mais leve – e mais acordada se você quiser. 💪\n\nMas nem sempre dar uma incapaz de se abrir no meio do dia: às vezes se dá bem deixar as tarefas que exigem alta atenção para outro momento. Eu posso organizar sua agenda, mesmo!  \n\n**E, caso queira das minhas piadas do tipo "Dormir agora e ter um sonho de cabelos de vampiro?":**\n\n> *“O que chamou o sono de “card” então? – Dado que era rude!*/\n  \nPronto? ✔️  \n\nQual dessas sugestões você quer tentar primeiro? Ou tem outra coisa que posso fazer para ajudar? 🌙✨	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	2	2026-07-17 04:43:56.601934+00	2026-07-17 04:44:04.144156+00	\N	\N	\N
6b2ab164-a34c-4ba9-9ca5-ef9b18373945	caecb51a-ca83-4c12-bcdb-7532eea0b13e	user	eu quero é dormir kkkkkkkkkkkk	completed	\N	\N	3	2026-07-17 04:44:48.425938+00	2026-07-17 04:44:48.425938+00	\N	\N	\N
8cd8c1de-f18d-410e-bc44-b4cda71ca913	caecb51a-ca83-4c12-bcdb-7532eea0b13e	user	menos oi ne carai. p q tanto oi	completed	\N	\N	7	2026-07-17 04:45:33.406602+00	2026-07-17 04:45:33.406602+00	\N	\N	\N
3b568149-db46-4a1b-b830-062021e8b03b	caecb51a-ca83-4c12-bcdb-7532eea0b13e	assistant	Entendido, Yuri! 🙏 Vou tirar o “oi” das respostas a partir de agora – é só você dizer “Ok, cheia de linho” quando quiser que eu volte a lavrar com alguns cumprimentos por padrão.\n\nE pra responder sua pergunta:  \n\n**Porque o GPT costuma abrir as mensagens com um como “Oi” à mão como forma de suavizar o tom, quase como se fosse um “aceno de boas-vindas”.**  \n- É uma estratégia de polidez e empatia que dá um começo amigável ao diálogo.  \n- É automatizado – o modelo tenta manter uma conversa natural, e o “oi” aparece como loop de cumprimento.  \n- Quando o modelo vê múltiplas mensagens de saudação em sequência, ele tende a repeti-las para garantir a cordialidade.\n\nSe for mais sua preferência, posso usar “E aí, Yuri?” ou “Tudo bem?” ou até mesmo começar direto com o assunto sem qualquer saudação. Me avisa!  \n\nVamos voltar a focar no que você precisa. Em que posso ajudar agora? 🚀	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	8	2026-07-17 04:45:33.406602+00	2026-07-17 04:45:38.05162+00	\N	\N	\N
cbf76a0c-40f9-4851-917c-a818da3cf097	3659528a-0a61-49c1-8185-fe6c964ca84b	user	eae	completed	\N	\N	1	2026-07-17 04:52:48.764992+00	2026-07-17 04:52:48.764992+00	\N	\N	\N
caf3ea15-4926-42d7-88d9-27b7be94c773	3659528a-0a61-49c1-8185-fe6c964ca84b	assistant	Eae! 🌟 Aqui é a Ella, seu assistente personal, pronto para fazer o dia de você (e do Yuri) de um jeito supercharmoso. Precisa de algum lembrete, dica rápida ou quer reorganizar a agenda? Só falar que eu tiro isso da mão e ainda arrumo tudo com aquele toque de brilho ✨!	completed	\N	NVIDIA NIM/openai/gpt-oss-20b	2	2026-07-17 04:52:48.764992+00	2026-07-17 04:52:52.018088+00	\N	\N	\N
\.


--
-- Data for Name: conversation_collections; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.conversation_collections (conversation_id, collection_id, created_at) FROM stdin;
\.


--
-- Data for Name: conversation_retrieval_settings; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.conversation_retrieval_settings (conversation_id, memory_enabled, rag_enabled, created_at, updated_at) FROM stdin;
48c7f217-f698-454d-87b5-54679d9e6875	t	t	2026-07-17 09:28:29.615743+00	2026-07-17 09:28:29.615743+00
caecb51a-ca83-4c12-bcdb-7532eea0b13e	t	t	2026-07-17 09:28:29.615743+00	2026-07-17 09:28:29.615743+00
3659528a-0a61-49c1-8185-fe6c964ca84b	t	t	2026-07-17 09:28:29.615743+00	2026-07-17 09:28:29.615743+00
84c6dfb4-c27f-4b31-8c09-15cb048955f6	t	t	2026-07-17 09:28:29.615743+00	2026-07-17 09:28:29.615743+00
aa92b814-105d-4290-8b61-23a85b701cc3	t	t	2026-07-17 09:28:29.615743+00	2026-07-17 09:28:29.615743+00
78ff6e53-e8ea-452b-bdb4-326b89f95ad8	t	t	2026-07-17 09:28:29.615743+00	2026-07-17 09:28:29.615743+00
10459f90-ca91-4878-9fdb-6f65d0d70eb5	t	t	2026-07-17 09:28:29.615743+00	2026-07-17 09:28:29.615743+00
\.


--
-- Data for Name: conversation_tools; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.conversation_tools (conversation_id, tool_id, created_at) FROM stdin;
\.


--
-- Data for Name: conversations; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.conversations (id, title, created_at, updated_at, persona_id, persona_name, persona_description, persona_instructions, persona_instruction_role) FROM stdin;
48c7f217-f698-454d-87b5-54679d9e6875	ooooooooooooooooooooi	2026-07-17 04:40:04.564281+00	2026-07-17 04:43:43.993604+00	00000000-0000-0000-0000-000000000011	Ella	Migrated from the original global persona.	Your name is Ella. And you is a charismatic personal assistant of Yuri.	system
caecb51a-ca83-4c12-bcdb-7532eea0b13e	cara, to com sono brabo	2026-07-17 04:43:56.492752+00	2026-07-17 04:45:38.050202+00	00000000-0000-0000-0000-000000000011	Ella	Migrated from the original global persona.	Your name is Ella. And you is a charismatic personal assistant of Yuri.	system
3659528a-0a61-49c1-8185-fe6c964ca84b	eae	2026-07-17 04:52:48.407478+00	2026-07-17 04:52:52.016646+00	00000000-0000-0000-0000-000000000011	Ella	Migrated from the original global persona.	Your name is Ella. And you is a charismatic personal assistant of Yuri.	system
84c6dfb4-c27f-4b31-8c09-15cb048955f6	manda uns textos em markdown ai pra eu testar se ta funfa...	2026-07-16 23:47:07.468454+00	2026-07-16 23:47:14.447291+00	00000000-0000-0000-0000-000000000011	Ella	Migrated from the original global persona.	Your name is Ella. And you is a charismatic personal assistant of Yuri.	system
aa92b814-105d-4290-8b61-23a85b701cc3	opa, eae	2026-07-17 00:43:42.202956+00	2026-07-17 00:43:45.290009+00	00000000-0000-0000-0000-000000000011	Ella	Migrated from the original global persona.	Your name is Ella. And you is a charismatic personal assistant of Yuri.	system
78ff6e53-e8ea-452b-bdb4-326b89f95ad8	oi, eae	2026-07-17 04:35:50.044866+00	2026-07-17 04:36:43.731725+00	00000000-0000-0000-0000-000000000011	Ella	Migrated from the original global persona.	Your name is Ella. And you is a charismatic personal assistant of Yuri.	system
10459f90-ca91-4878-9fdb-6f65d0d70eb5	oooooooooooooooooi	2026-07-17 04:37:28.844898+00	2026-07-17 04:38:41.504929+00	00000000-0000-0000-0000-000000000011	Ella	Migrated from the original global persona.	Your name is Ella. And you is a charismatic personal assistant of Yuri.	system
\.


--
-- Data for Name: image_model_profiles; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.image_model_profiles (model_id, supports_generation, supports_editing, supports_multiple_inputs, supports_masks, max_input_images, default_size, default_quality, default_output_format, default_background, default_count, default_input_fidelity, provider_parameters, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: image_operation_inputs; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.image_operation_inputs (operation_id, asset_id, input_type, "position") FROM stdin;
\.


--
-- Data for Name: image_operation_outputs; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.image_operation_outputs (operation_id, asset_id, "position") FROM stdin;
\.


--
-- Data for Name: image_operations; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.image_operations (id, conversation_id, user_message_id, assistant_message_id, model_cache_entry_id, operation_type, status, provider_model_id, prompt, revised_prompt, parameters, error_code, error_message, started_at, finished_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: knowledge_chunks; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.knowledge_chunks (id, document_id, "position", content, character_count, embedding, created_at) FROM stdin;
\.


--
-- Data for Name: knowledge_collections; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.knowledge_collections (id, name, description, enabled, default_enabled, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: knowledge_documents; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.knowledge_documents (id, collection_id, filename, media_type, size_bytes, content_sha256, extracted_text, status, error_message, chunk_count, embedding_model_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: mcp_servers; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.mcp_servers (id, name, transport, url, command, arguments, encrypted_headers, header_names, encrypted_environment, environment_names, enabled, timeout_seconds, last_sync_status, last_sync_at, last_error, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: mcp_tools; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.mcp_tools (id, server_id, name, public_name, description, input_schema, enabled, default_enabled, requires_confirmation, is_available, last_seen_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: media_assets; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.media_assets (id, source_type, storage_key, original_filename, media_type, size_bytes, content_sha256, width, height, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: memories; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.memories (id, persona_id, content, category, enabled, source_type, source_conversation_id, embedding, embedding_model_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: memory_suggestions; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.memory_suggestions (id, conversation_id, persona_id, content, category, status, created_at, resolved_at) FROM stdin;
\.


--
-- Data for Name: message_attachments; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.message_attachments (message_id, asset_id, attachment_type, "position", created_at) FROM stdin;
\.


--
-- Data for Name: model_cache_entries; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.model_cache_entries (id, endpoint_id, model_id, is_manual, is_available, first_seen_at, last_seen_at, created_at, updated_at) FROM stdin;
f0551f56-36fc-4c16-8142-8a6a2f644588	e383c6da-a54b-4224-986e-deee71353d2f	agnes/agnes-1.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b12fd7df-7f22-465e-93ec-083d392a751f	e383c6da-a54b-4224-986e-deee71353d2f	agnes/agnes-2.0-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1e686ff9-ada8-4c39-ad25-a83c5176781b	e383c6da-a54b-4224-986e-deee71353d2f	agnes/agnes-image-2.0-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0d484fc0-b10d-45a3-87c6-4e94606b3e3f	e383c6da-a54b-4224-986e-deee71353d2f	agnes/agnes-image-2.1-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2114598c-a0e1-4cef-b8cc-80ef2c0f8529	e383c6da-a54b-4224-986e-deee71353d2f	agnes/agnes-video-v2.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0f09da01-19f9-49d0-bfec-56d88b471d6a	e383c6da-a54b-4224-986e-deee71353d2f	cerebras/gemma-4-31b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0c6617ef-09a6-433d-b98c-966aee8d7ad2	e383c6da-a54b-4224-986e-deee71353d2f	cerebras/gpt-oss-120b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c8f1e785-7523-4087-a910-2527ae3d3079	e383c6da-a54b-4224-986e-deee71353d2f	cerebras/zai-glm-4.7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f36ac5a5-1208-4f21-a761-d5a5dc3fe6a8	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/aisingapore/gemma-sea-lion-v4-27b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5052f415-5a13-4255-802c-43a5474f19ff	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/deepseek-ai/deepseek-r1-distill-qwen-32b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b5097c72-aba3-4d75-9460-01cc82022ec6	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/google/gemma-4-26b-a4b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
777e4e86-5bb1-4dab-85df-cfdb30da2242	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/ibm-granite/granite-4.0-h-micro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
212d3c87-9b5e-4d9b-bd10-0f807122eb7e	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/meta/llama-3.1-8b-instruct-fp8	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
dde10bf2-56ae-4dd4-9d07-de4d358a31cc	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/meta/llama-3.2-11b-vision-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
831271a7-642a-4b0b-a226-31351b5f973c	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/meta/llama-3.2-1b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0692b147-58ee-4377-8069-a71429d3bff7	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/meta/llama-3.2-3b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
df3bde2f-632f-4cbf-8bea-a9bd3f7263a7	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/meta/llama-3.3-70b-instruct-fp8-fast	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
72c07356-da82-4cf0-9727-323f0bda5be9	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/meta/llama-4-scout-17b-16e-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c4dc3374-69b8-47d8-a0a8-8a461edeab73	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/meta/llama-guard-3-8b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d31446d4-43d3-44ed-b98e-6375814dee88	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/mistralai/mistral-small-3.1-24b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
35877bed-38ea-48ed-8484-acf37d88ac6c	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/moonshotai/kimi-k2.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5a5d0bbf-bc4b-4c75-a79c-41013220e490	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/moonshotai/kimi-k2.7-code	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
59c27c3d-b288-40c0-8733-338bb2d3e449	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/nvidia/nemotron-3-120b-a12b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1d057cbb-9fc4-469b-aeb3-feb1a83ccde8	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/openai/gpt-oss-120b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5e872938-08fd-4b37-b586-70a1afe356b3	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/openai/gpt-oss-20b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0acbd5a5-cd0d-4015-8e02-4f06c7e1ee93	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/qwen/qwen2.5-coder-32b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c417597b-a7f8-4672-9c64-dc5f756e6c79	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/qwen/qwen3-30b-a3b-fp8	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
140d59e3-2aae-4780-a036-d8cde9b2c7dd	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/qwen/qwq-32b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e3fab052-55e8-4331-ae8f-68fb96906826	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/zai-org/glm-4.7-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a13f409b-0f93-4881-903c-c10f0e12d6ca	e383c6da-a54b-4224-986e-deee71353d2f	cloudflare/@cf/zai-org/glm-5.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3a890366-9cb2-466d-878f-cf4779a988d2	e383c6da-a54b-4224-986e-deee71353d2f	cohere/c4ai-aya-expanse-32b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9e37f5cc-b193-4c92-bf67-3f407f8cf64c	e383c6da-a54b-4224-986e-deee71353d2f	cohere/c4ai-aya-vision-32b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
77d67890-62eb-499f-9057-87223f28b9d1	e383c6da-a54b-4224-986e-deee71353d2f	cohere/cohere-transcribe-03-2026	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5ddd6eea-15f0-43c0-8503-906e8e64674c	e383c6da-a54b-4224-986e-deee71353d2f	cohere/command-a-03-2025	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
663d46b4-f020-4f3f-9763-d4705df5e4d5	e383c6da-a54b-4224-986e-deee71353d2f	cohere/command-a-plus-05-2026	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f55a62d4-3983-41a5-abb6-b5b79f3fcee3	e383c6da-a54b-4224-986e-deee71353d2f	cohere/command-a-reasoning-08-2025	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3f651e00-8f7f-4881-887a-0f7b3565167a	e383c6da-a54b-4224-986e-deee71353d2f	cohere/command-a-translate-08-2025	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7e9971f5-6deb-4e66-a33c-d5f94901551c	e383c6da-a54b-4224-986e-deee71353d2f	cohere/command-a-vision-07-2025	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9f8d0629-8501-44f4-9956-6a4e88fef828	e383c6da-a54b-4224-986e-deee71353d2f	cohere/command-r-08-2024	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3257c32e-b556-4619-b9f7-66ce02c4ac50	e383c6da-a54b-4224-986e-deee71353d2f	cohere/command-r-plus-08-2024	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a4552f79-df7e-4f1b-94ac-5e2e905a8c78	e383c6da-a54b-4224-986e-deee71353d2f	cohere/command-r7b-12-2024	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9da21b70-a548-455a-b3d4-0497810cca43	e383c6da-a54b-4224-986e-deee71353d2f	cohere/command-r7b-arabic-02-2025	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
be7a0045-69e3-4a99-950a-dc8a2ed95b98	e383c6da-a54b-4224-986e-deee71353d2f	cohere/embed-english-light-v3.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
386b0087-d022-44e0-89bf-a4493ac22fb5	e383c6da-a54b-4224-986e-deee71353d2f	cohere/embed-english-light-v3.0-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
71670f37-e51f-42c6-8e31-2aeef48a8c76	e383c6da-a54b-4224-986e-deee71353d2f	cohere/embed-english-v3.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5e577682-e78e-4321-af65-1aa1914e93ee	e383c6da-a54b-4224-986e-deee71353d2f	cohere/embed-english-v3.0-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
68257af2-1ef5-445d-a575-0e68bdb426ba	e383c6da-a54b-4224-986e-deee71353d2f	cohere/embed-multilingual-light-v3.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
edccf5f2-4e8a-4000-a5c7-5cae8440ffb2	e383c6da-a54b-4224-986e-deee71353d2f	cohere/embed-multilingual-light-v3.0-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
116c117e-4a91-4405-bbfa-281a2853b2a4	e383c6da-a54b-4224-986e-deee71353d2f	cohere/embed-multilingual-v3.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e450e941-c84c-4ec1-bd7b-81727533db69	e383c6da-a54b-4224-986e-deee71353d2f	cohere/embed-multilingual-v3.0-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4be76b41-a6d7-4125-b789-2b89ee63ea0d	e383c6da-a54b-4224-986e-deee71353d2f	cohere/embed-v4.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
eb6df051-e171-41c0-89f0-780d878838a0	e383c6da-a54b-4224-986e-deee71353d2f	cohere/north-mini-code-1-0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
771f6ba1-77b8-400d-be70-991ca8336d71	e383c6da-a54b-4224-986e-deee71353d2f	cohere/rerank-english-v3.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d2ba471a-3715-4816-bfdb-9c2726053da7	e383c6da-a54b-4224-986e-deee71353d2f	cohere/rerank-multilingual-v3.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6c7ab5b8-c340-457d-8868-b664511a3039	e383c6da-a54b-4224-986e-deee71353d2f	cohere/rerank-v3.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fd0b04be-2b08-4a76-b3ec-f8951ee0a332	e383c6da-a54b-4224-986e-deee71353d2f	cohere/rerank-v4.0-fast	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0c00b111-3376-4366-9ea1-c01868c58735	e383c6da-a54b-4224-986e-deee71353d2f	cohere/rerank-v4.0-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fbd8da76-d660-4919-b20f-2bb1a8a19992	e383c6da-a54b-4224-986e-deee71353d2f	cohere/tiny-aya-earth	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
81883cfe-979e-460f-9aa7-c01310a5690e	e383c6da-a54b-4224-986e-deee71353d2f	cohere/tiny-aya-fire	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d5d36844-573b-44be-b9fb-87f25c0603bf	e383c6da-a54b-4224-986e-deee71353d2f	cohere/tiny-aya-global	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8fbb112e-64b4-481c-a758-7303e900786d	e383c6da-a54b-4224-986e-deee71353d2f	cohere/tiny-aya-water	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
96363180-d463-4fd7-b789-0c732d38b833	e383c6da-a54b-4224-986e-deee71353d2f	gemini/antigravity-preview-05-2026	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c6a95d6a-7ba6-43e6-a415-f8bef59c4d8c	e383c6da-a54b-4224-986e-deee71353d2f	gemini/aqa	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f2264d8d-ade4-4259-8494-53624ddb5287	e383c6da-a54b-4224-986e-deee71353d2f	gemini/deep-research-max-preview-04-2026	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5fff43d1-1c7c-416c-b442-e43f16d8d4ba	e383c6da-a54b-4224-986e-deee71353d2f	gemini/deep-research-preview-04-2026	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4a11ad82-4f82-4526-b662-7ab0108d6856	e383c6da-a54b-4224-986e-deee71353d2f	gemini/deep-research-pro-preview-12-2025	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e1f5f069-ee2e-4bb4-bce4-ce70731564b5	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.0-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
917c2694-7d37-4bea-bff0-6c8d15bcdcb7	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.0-flash-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
902569c4-51cf-43d7-b1c5-420790317ef1	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.0-flash-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
484f1cea-1c56-4746-a3fa-8ae34e4b2283	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.0-flash-lite-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0766dc95-6aad-49b6-bcf5-778f8a77cc08	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.5-computer-use-preview-10-2025	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7462d46c-b550-4606-b26c-2f4414342d5f	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
53287b5a-1552-47a2-b20a-f248a85032f3	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.5-flash-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
154faacb-5d08-4e37-ac45-419a21ac805d	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.5-flash-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1985b5ed-a39f-4832-8307-0b60cbafa558	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.5-flash-native-audio-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
60fb38e6-fb2d-4416-a75b-7b30eea9268c	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.5-flash-native-audio-preview-09-2025	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
af5343f2-881f-4e3e-916b-960b3dde72d9	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.5-flash-native-audio-preview-12-2025	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
66cd7089-7d1e-41dc-b60e-4f32699f0176	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.5-flash-preview-tts	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7b9f1b68-0233-4f84-a5c3-5b1175a58057	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.5-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
27df29ad-8a0e-4320-8eef-944533c1fca4	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-2.5-pro-preview-tts	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c2655bdb-255e-48e5-8434-13c2d19cea55	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3-flash-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2a7a8c0c-c8d3-49dc-8f6d-caebfcc3037a	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3-pro-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
84f6d453-3a32-4cdf-8eb9-a6c724ceb11a	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3-pro-image-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c8e12d38-2c38-40bf-84d4-6c3782472be2	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3-pro-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d0f52d2b-c675-40a9-a665-9055980bf37d	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3.1-flash-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8f1f336e-93ce-437b-8f14-c6e06290b1a8	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3.1-flash-image-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c142aecd-c7a6-49b9-9a10-e4d78ae29401	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3.1-flash-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
531d9a18-97c4-4b81-bca5-e1f8f7a9eaf7	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3.1-flash-lite-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
24f132ae-1ffe-4ddd-b64c-fd746d12b846	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3.1-flash-lite-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
efe9b8f2-88d4-4d3b-997a-18a706853056	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3.1-flash-live-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
60c4347a-452c-4652-8e6a-3592c7fc5b67	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3.1-flash-tts-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bc644c3d-1192-4dbf-bc06-d5243fdbe41c	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3.1-pro-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c26bedb9-01b1-4653-979f-a09998098803	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3.1-pro-preview-customtools	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
51585ecb-1da8-437f-895f-f70528932a37	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bbd41ca9-d515-4b51-a260-f9e2a0bac2f9	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-3.5-live-translate-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8677fb81-a2fc-48fe-9ae3-9df057cab110	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-embedding-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8bbe8d67-25e2-4992-b79f-9e64b4743a02	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-embedding-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d76b960a-4235-40df-bab2-61fb3591efc3	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-embedding-2-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
80a758c2-ba8a-44e9-81f8-170e64f99765	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-flash-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ebf1609a-e099-48d1-a3e9-127184cfb7fe	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-flash-lite-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5e2926db-170f-40db-8372-dd239a1d0a73	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-omni-flash-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8adf677a-d525-4995-bda9-87db2504348b	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-pro-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5b653b24-cf01-4589-b3cc-de150d6a5fcb	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-robotics-er-1.5-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6c5a74d0-1624-46bc-a865-bfa2f9041241	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemini-robotics-er-1.6-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1f7d3f19-1883-48d4-8462-689cd1b3f136	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemma-4-26b-a4b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
126e571b-d839-4c83-beef-b819d02c1c57	e383c6da-a54b-4224-986e-deee71353d2f	gemini/gemma-4-31b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
caf1b4d2-4c85-4f46-8b94-930313a360fd	e383c6da-a54b-4224-986e-deee71353d2f	gemini/imagen-4.0-fast-generate-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
568a84c0-5c3a-452b-b04e-f5cc0329a54e	e383c6da-a54b-4224-986e-deee71353d2f	gemini/imagen-4.0-generate-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
14b4f3ed-5c32-4ffd-9d4a-d4421b755eef	e383c6da-a54b-4224-986e-deee71353d2f	gemini/imagen-4.0-ultra-generate-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b0760f6e-ef93-4811-8788-93b1c081f9e2	e383c6da-a54b-4224-986e-deee71353d2f	gemini/lyria-3-clip-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
364cd505-2e45-446e-a7e6-276f0e0c4b50	e383c6da-a54b-4224-986e-deee71353d2f	gemini/lyria-3-pro-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
41e66bd8-71af-4cf2-bb92-181cc6b8bad2	e383c6da-a54b-4224-986e-deee71353d2f	gemini/nano-banana-pro-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b6c43f0f-f878-4f6d-9ea1-a2ec50a5e42d	e383c6da-a54b-4224-986e-deee71353d2f	gemini/veo-3.1-fast-generate-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d0b42137-0401-489b-baa5-45c00cff0387	e383c6da-a54b-4224-986e-deee71353d2f	gemini/veo-3.1-generate-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
74c0e6c9-2ece-42b0-9c7a-b5dcda15042f	e383c6da-a54b-4224-986e-deee71353d2f	gemini/veo-3.1-lite-generate-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1222df4b-4459-4fff-8189-af52b80b08a0	e383c6da-a54b-4224-986e-deee71353d2f	groq/allam-2-7b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d489ecfc-df5b-4140-aa5c-43e535c6db7d	e383c6da-a54b-4224-986e-deee71353d2f	groq/canopylabs/orpheus-arabic-saudi	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6d888fd7-10aa-4208-86fa-b136bfba7b7b	e383c6da-a54b-4224-986e-deee71353d2f	groq/canopylabs/orpheus-v1-english	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5d4bc713-2779-41e9-8d20-fdfeef28ab3a	e383c6da-a54b-4224-986e-deee71353d2f	groq/groq/compound	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
315ba46d-60bc-4f4c-b388-6669d3e69b96	e383c6da-a54b-4224-986e-deee71353d2f	groq/groq/compound-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3a989c24-961d-4412-9c54-1c5e4357ce04	e383c6da-a54b-4224-986e-deee71353d2f	groq/llama-3.1-8b-instant	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c08d781b-d32f-462b-962b-760adb1374c0	e383c6da-a54b-4224-986e-deee71353d2f	groq/llama-3.3-70b-versatile	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5ba7823d-4bbd-4cde-8dac-6fb787a5dcde	e383c6da-a54b-4224-986e-deee71353d2f	groq/meta-llama/llama-4-scout-17b-16e-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
12a5c532-4c10-4b40-9a9d-6f11f69da176	e383c6da-a54b-4224-986e-deee71353d2f	groq/meta-llama/llama-prompt-guard-2-22m	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b617a763-3609-4388-b077-be5082cd621d	e383c6da-a54b-4224-986e-deee71353d2f	groq/meta-llama/llama-prompt-guard-2-86m	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bc77aa66-5f66-4059-8388-8daf4d90defd	e383c6da-a54b-4224-986e-deee71353d2f	groq/openai/gpt-oss-120b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
79e88816-d878-4c76-a189-28788c8933d1	e383c6da-a54b-4224-986e-deee71353d2f	groq/openai/gpt-oss-20b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a25d0e0e-67b2-441f-b151-fef70f746977	e383c6da-a54b-4224-986e-deee71353d2f	groq/openai/gpt-oss-safeguard-20b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5c8b6c92-52e6-497f-b069-45955da9a194	e383c6da-a54b-4224-986e-deee71353d2f	groq/qwen/qwen3-32b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f36af8d6-e02a-4fe9-9584-84aa69e9f59c	e383c6da-a54b-4224-986e-deee71353d2f	groq/qwen/qwen3.6-27b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5d2050ad-12aa-41f4-b96e-1c4ebf162bdd	e383c6da-a54b-4224-986e-deee71353d2f	groq/whisper-large-v3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6619f8c1-969f-4428-b189-cd79754088ae	e383c6da-a54b-4224-986e-deee71353d2f	groq/whisper-large-v3-turbo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d76832ac-9fb7-49aa-9ebc-66be5586db35	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/ai21/jamba-large-1.7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
79691fc6-e981-489c-a930-ff128e680291	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/aion-labs/aion-2.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2830f06a-1b2b-42f4-b3cf-9ac3d31666fd	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/aion-labs/aion-3.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bfb96d3b-e1f6-4245-99ee-a03585fbe919	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/aion-labs/aion-3.0-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
03ae5499-565e-48ea-acba-d5f10219a1e5	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/aion-labs/aion-rp-llama-3.1-8b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
38f0ae62-4596-46ee-95db-c6880120cb40	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/allenai/olmo-3-32b-think	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f21f2d29-0dd2-43f3-82fc-bfced594ae3d	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/amazon/nova-2-lite-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fcf0ad00-f989-440b-bd02-a0b7d78a92c6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/amazon/nova-lite-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a40dc7ec-66c1-401b-a098-7ff8044733e0	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/amazon/nova-micro-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
30d12d5f-6fb6-44ac-876a-10435c1a2642	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/amazon/nova-premier-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
31ca3988-a680-4fb8-a478-76e87e8c5821	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/amazon/nova-pro-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d4d5e5ad-dcdf-410a-8387-6430b0ca2016	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthracite-org/magnum-v4-72b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
22c0219d-999c-4236-9969-c032322f10a7	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-3-haiku	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f0f89485-f8c4-4013-b605-77847849ef25	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-fable-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9e5cab02-090b-4554-b9d7-666dd3eaf7ee	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-haiku-4.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fb1a075b-4236-4ce3-91ae-384d6820eaaa	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-opus-4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7e740ac8-b4b2-4f91-b20e-9a6ef40f7617	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-opus-4.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
456ae97e-06ad-4ff9-a8ed-ac09f9b0f8c8	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-opus-4.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c28de790-33c4-41d5-a27e-fe2c819f506d	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-opus-4.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
923ed714-bdc9-4378-9d77-ec76b4bb25b2	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-opus-4.7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
61954c66-bb45-412a-80b5-d8e27002e5b2	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-opus-4.7-fast	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
275d04ac-18ce-42e4-83e8-f103d7691a9c	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-opus-4.8	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3578e447-b35b-4c5b-bb96-6929bcf9f2eb	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-opus-4.8-fast	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
105200b5-e710-4445-84c5-411098f39787	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-sonnet-4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
74ea2a46-110b-488e-ab25-ab685c633f6e	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-sonnet-4.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
12d2f9f3-b8c7-4570-ac46-5d0c63f8a381	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-sonnet-4.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
487576d2-33b1-4dd3-b3c6-d82d01e2a309	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/anthropic/claude-sonnet-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e647bb53-9b20-4687-a019-89902ea79461	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/arcee-ai/trinity-large-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
eb792a0f-a058-4ad8-b634-5b4f1aa63e27	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/arcee-ai/virtuoso-large	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
478f4142-442d-4399-b3c0-bd3bfc90e287	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/baidu/ernie-4.5-vl-424b-a47b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a6bcef6c-8a04-4a2a-a62c-38dbf386b7b1	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/bytedance-seed/seed-1.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3bca5bd0-be16-4b0f-a76c-d519d98a9e9a	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/bytedance-seed/seed-1.6-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ee99e2cf-fe94-454e-a123-3fafb61d5653	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/bytedance-seed/seed-2.0-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5f57fde8-6e2c-4c3c-936e-7331f8642f9e	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/bytedance-seed/seed-2.0-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
dd66bed1-4f40-4b54-9701-d2c69762b6b2	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/bytedance/ui-tars-1.5-7b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
dc362f19-a935-4288-bbf7-4bfdd9992395	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/cognitivecomputations/dolphin-mistral-24b-venice-edition	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e3806fce-cc59-4c32-8add-ae54436af988	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/cohere/command-a	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d8fdb5e1-3ddb-476f-ae6c-701161cb2494	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/cohere/command-r-08-2024	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c78cab96-f380-41a6-9d5a-02fa95d7b46c	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/cohere/command-r-plus-08-2024	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
50267515-6a6f-446e-b8e5-79c2c7a118aa	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/cohere/command-r7b-12-2024	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
85e16c87-471f-42c6-ae52-cece31561aa5	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/cohere/north-mini-code:free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d6d94eaf-aa0a-48f2-b5f8-b1054457e5fb	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepcogito/cogito-v2.1-671b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
986cf381-f53e-4544-8ac1-820dafe93dfc	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-chat	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
55d89e62-987f-493f-bc07-7d98493a15c3	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-chat-v3-0324	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
dac1712c-8479-41a1-9116-f1930168f32c	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-chat-v3.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
33abdbb2-5d26-4a0c-b2c1-223c351def8f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-r1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
369b7213-d331-445c-b13f-96aed2b69914	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-r1-0528	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e0d59356-5d15-45b6-812e-789f56b15791	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-r1-distill-llama-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
303abc21-4897-43a6-bd4e-35a549566db0	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-v3.1-terminus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d4324410-04ab-412b-959b-fb92d12bd788	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-v3.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bebe0ec4-1ad2-41ee-8482-bff7ca041f50	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-v3.2-exp	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4165b484-ea5f-40c0-82de-b22a29dcca5d	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-v4-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
113309fd-7bdd-4bba-9be5-5dd4c7a2852f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-v4-flash:discounted	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d602fb3e-03a6-4f96-b116-efebf3cebc88	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-v4-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
92707e1b-163b-497d-bf49-b3ec4cfb3922	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/deepseek/deepseek-v4-pro:discounted	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1142b0ed-d877-4e5e-91df-7ed184629e58	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-2.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
66986eed-8ab5-4e91-b8f0-c990d2f62a9f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-2.5-flash-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a4565e6e-1e71-4e68-aff5-1532a40b4759	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-2.5-flash-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
710ce3df-a5ba-48d3-8271-fcca65a667e7	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-2.5-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
365e2c98-77b7-4738-96ff-b8f4572790c9	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-2.5-pro-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
20774b51-bc03-4a40-9cc6-e9eced0cdd2a	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-2.5-pro-preview-05-06	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f7b98948-f652-4bd6-9e8d-6251ca223a9f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-3-flash-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
458574a2-8b51-4e6b-920d-c81cbe5cad98	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-3-pro-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
86907554-b846-4200-8c20-16559a75df67	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-3-pro-image-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a4b4383c-b3a7-407a-b03a-4011567dbccb	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-3.1-flash-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bbd97765-b625-4e26-a9c6-c330dbe10ea1	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-3.1-flash-image-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
56a5d71a-587d-461f-9485-8197158aa40a	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-3.1-flash-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
34bc798c-66bd-4111-8ae8-c7d76c384ea5	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-3.1-flash-lite-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
16b36800-6747-4b24-943a-ece738f34226	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-3.1-flash-lite-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
942d1a07-893d-45db-bcaa-e5ba185b2219	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-3.1-pro-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
17948e20-1cb1-472a-adbd-be8a60c71604	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-3.1-pro-preview-customtools	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
88434da9-49a8-48a9-ac0f-767082bb9afa	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemini-3.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0311c3fa-63ff-4d5c-91af-bfe79d7496d7	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemma-2-27b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d4ed4590-efbc-4d1a-b83b-c433255410ce	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemma-3-12b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
89ad7753-4a46-4c15-901c-b07e8f196844	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemma-3-27b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
82c6cb3b-f744-49bb-89a9-bb570a7cadc4	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemma-3-4b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
33ac8cd2-4eed-46ef-9293-0549c8d7da58	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemma-3n-e4b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
641c142f-e8ac-40b5-9b9f-344e7614d272	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemma-4-26b-a4b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
261f18d9-bd83-41f7-8fd2-9265a2e07e65	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/gemma-4-31b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
91864c58-03d1-4324-b4fe-c700ce1236c5	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/lyria-3-clip-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4784e568-dae6-4b7e-9e36-34708647d49b	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/google/lyria-3-pro-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ec08cef7-1b2f-4ea4-9ca7-e6c9e2f54602	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/gryphe/mythomax-l2-13b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
37fedf8a-909a-4bde-9fab-e3778abe2d15	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/ibm-granite/granite-4.0-h-micro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
44e1499f-9fd8-4790-b512-a9638e5e32f3	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/ibm-granite/granite-4.1-8b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e2812d66-1d62-4ecf-91c8-674ae38eb254	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/inception/mercury-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
92bd75f8-d1ff-4c32-b27f-fe264122aafa	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/inclusionai/ling-2.6-1t	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
17d1472f-af8a-4b67-ba86-86fc1ba056c0	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/inclusionai/ling-2.6-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
656a963a-2512-43f5-ae5f-12b2e34cd368	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/inclusionai/ring-2.6-1t	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5a31f3b6-668c-4a80-82ac-7a7413a49dc5	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/inflection/inflection-3-pi	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a0e65df3-612f-45e8-9a3d-351d4410708f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/inflection/inflection-3-productivity	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
540caf18-fedc-456a-8647-6e0ea09bb89c	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/kilo-auto/balanced	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
09e7da62-348b-4d50-bf45-ee2bb983f811	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/kilo-auto/efficient	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e211dc4f-39d5-4228-8766-d61adeaca959	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/kilo-auto/free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2d6db767-cb8a-4dfb-9736-401338be2296	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/kilo-auto/frontier	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b5ca4a0d-750f-48c3-ae83-d743813e3dd4	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/kilo-auto/small	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4bd43695-cc89-48c4-966d-5d5e56ef7325	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/kwaipilot/kat-coder-pro-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e9050bae-7541-4fc8-a109-0c77d55a7584	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mancer/weaver	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1a394c13-b1ce-41ff-b9d1-024128f05358	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/meta-llama/llama-3.1-70b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
06ac7286-c277-448a-b70f-fde68c6bb327	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/meta-llama/llama-3.1-8b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9a7f4bb1-c585-4461-8bd1-01bacfd8bcac	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/meta-llama/llama-3.2-11b-vision-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f37ef83c-41d0-438a-b9bc-c3e8b3bcd117	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/meta-llama/llama-3.2-1b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f983f1fc-df07-43f2-9793-2daef97579b9	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/meta-llama/llama-3.2-3b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3b5136a8-a1a8-48de-91f0-a66880ccdb42	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/meta-llama/llama-3.3-70b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
652b6989-370d-42a4-9d83-bc7541f58552	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/meta-llama/llama-4-maverick	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4d991cfc-5243-4ac2-9130-9f768f6b8adb	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/meta-llama/llama-4-scout	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5eb461cc-1e8b-4f51-a1a0-4c8e58ace297	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/meta-llama/llama-guard-4-12b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
84f89601-a636-412b-ba78-e4d214c0590c	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/microsoft/phi-4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9f3fa217-f55b-44da-b8e9-437f03ac75d8	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/microsoft/wizardlm-2-8x22b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
23ece639-367f-49d0-9e40-42b7c5fb7bd7	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/minimax/minimax-01	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
23bb8d2d-b613-49e1-a166-c68d5711abbc	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/minimax/minimax-m1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4cab5b3d-1682-4a0b-a66d-b4777430c3c7	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/minimax/minimax-m2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4552a43d-c733-4623-811d-471984361749	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/minimax/minimax-m2-her	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ff084f6c-6dd0-45d9-9bec-dc3738df4dcd	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/minimax/minimax-m2.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7f4c9f4b-feb0-4c57-8c6e-593e21c48eb9	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/minimax/minimax-m2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f6446c5c-147d-419a-b236-18129c715fc0	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/minimax/minimax-m2.7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a82d75f5-33f4-4d60-81e1-2e7f5c6d0883	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/minimax/minimax-m3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bb3cdcf0-e568-4611-91a0-a5cc4ef86636	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/codestral-2508	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
36e00be8-a5c4-4ec3-8d4b-4395d0e3f069	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/devstral-2512	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e9ff56f7-8290-4410-859f-a85c229d8998	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/ministral-14b-2512	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
23e83427-2920-47f6-b60e-17ca8ed1c8ae	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/ministral-3b-2512	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0c90f07a-6f88-4e65-bdc4-9b6f1dc7b4b1	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/ministral-8b-2512	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c88e956e-99f4-4a11-9fa8-8747046bed91	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mistral-large	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c5d52018-c21a-41bf-a549-876064b998b6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mistral-large-2407	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6c7904f2-061a-4a51-8562-1f71c5b5206f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mistral-large-2512	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
511df57c-94d0-4f6e-924f-8ccb59bf0e00	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mistral-medium-3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
95a773b8-4f59-4062-aaf2-4ea84d755f88	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mistral-medium-3-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
354799d4-8345-4ea1-b037-96f461fbbfed	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mistral-medium-3.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
22eb8fe1-c86e-4ae7-b54f-cccb72e805e9	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mistral-nemo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d01a5bed-c138-4b3d-b331-145fb2adff1f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mistral-saba	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
af8d4694-f10f-4326-b139-70f49321d814	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mistral-small-24b-instruct-2501	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
38e60eb5-4a0f-4604-b9cd-4a159360bf09	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mistral-small-2603	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9ad8a1fc-9507-4c11-9e6c-5ccbd36dbe4f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mistral-small-3.1-24b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2f8fb327-bd84-4e7c-8273-3bc5611e9429	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mistral-small-3.2-24b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4f823280-c5a0-44d6-8a68-9d86cd3db61a	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/mixtral-8x22b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1db60bba-bb12-4f71-89fc-204db3263ebf	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/mistralai/voxtral-small-24b-2507	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
be88c48b-90b2-448d-a4e9-c226d0f8e9f1	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/moonshotai/kimi-k2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
30615ba0-9b9c-4e16-a27f-97f7f06d340b	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/moonshotai/kimi-k2-0905	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
30f66d7f-ee61-4efb-bcf9-08438990be8c	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/moonshotai/kimi-k2-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2cbc338f-aac4-438c-bf83-c48e2df02d7b	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/moonshotai/kimi-k2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e8845255-c426-4f00-8e44-3e6950f38100	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/moonshotai/kimi-k2.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
998e98fa-f356-430e-981c-1ce83b9a9335	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/moonshotai/kimi-k2.7-code	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1b4a1d4f-8823-42ed-bcfd-77b24b54cb82	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/morph/morph-v3-fast	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
dd711091-cc0a-49e4-a27b-10f4fc62b2b6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/morph/morph-v3-large	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4889c8ae-7da4-4d5d-acc3-2912f5c46f52	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nex-agi/nex-n2-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
23247a0e-833d-49ea-87bd-270394a3952d	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nex-agi/nex-n2-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7653cd08-4a75-4b57-893a-daf3cee6a339	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nousresearch/hermes-3-llama-3.1-405b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6317dff4-e4f4-4a4f-9e03-999f116377cc	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nousresearch/hermes-3-llama-3.1-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d0f47169-8083-4f72-8ffb-38837cf8c5e8	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nousresearch/hermes-4-405b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b9adaedd-7d09-495b-bea9-e939a583961a	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nousresearch/hermes-4-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
aa329f0d-424d-4ebe-9d44-c98ea95a8444	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nvidia/llama-3.3-nemotron-super-49b-v1.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
dd6aabc9-b0af-4227-8197-5a9359192072	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nvidia/nemotron-3-nano-30b-a3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f0c343ef-dc05-48c8-93f4-14f01a2313b6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c9bcd56d-9f55-4d85-8db8-289969ebe6c6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nvidia/nemotron-3-super-120b-a12b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
70790a73-f0d5-4e9b-803e-30e92091402d	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nvidia/nemotron-3-super-120b-a12b:free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ab89ef8c-2bb0-4284-a2a1-c86256ee1bad	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nvidia/nemotron-3-ultra-550b-a55b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ac02f501-2460-40bc-b4ec-e2586e3d3f03	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nvidia/nemotron-3-ultra-550b-a55b:free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f3897021-848d-4831-b9d0-c6ac8a86e285	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/nvidia/nemotron-3.5-content-safety:free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cb2ad385-7e52-48b5-b0f4-423e1a9b6e9f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-3.5-turbo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d23a4d1f-edb9-496f-b0c1-9446d24ea642	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-3.5-turbo-0613	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
521a5674-27a5-495f-95ce-e94c074763c6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-3.5-turbo-16k	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3f5359e2-eac1-40a6-9eb6-78361f7e0a06	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-3.5-turbo-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4157acae-4350-40b4-a836-802fa869218c	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
af70eb0c-6d73-484a-8abf-1164616c0f9d	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4-turbo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ae182ce5-be90-4675-ae83-a94ecee318ff	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4-turbo-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
617b1f61-927c-45a4-98ee-28ba7ff5a0dc	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
29cf9cde-155a-47d4-aa14-4c507bf0b1b4	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4.1-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d12b0d53-3d8a-4ef7-a005-e826b7de9532	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4.1-nano	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
39dda82e-ca9e-4f62-b9f2-1d1e329ce5ea	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4o	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
01f34a73-cf91-42bd-8b10-7e986d68add1	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4o-2024-05-13	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9403146f-997a-4ec5-8f3e-fe1004292808	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4o-2024-08-06	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cde12fd5-4d05-4725-82e1-6404b91c1718	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4o-2024-11-20	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
01573ef8-8421-417a-a8ff-c27ee6fc715b	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4o-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
960e7b12-ad48-462d-aad0-0879b1252ea9	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4o-mini-2024-07-18	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b57f2a90-1e6b-4348-8f0a-08b96e740705	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4o-mini-search-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4e895c76-b126-49ce-b05b-923dc7485c42	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-4o-search-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7b7c875b-9cf5-4c72-be66-2b0cd9c15ce9	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
df03b939-6f75-4e14-b21b-d71dc161f74f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5-chat	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8def3577-9422-4f84-bba4-15804f4ef1be	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5-codex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1acb5c8a-cd57-4be2-917d-4b1946fdc8d2	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ad8f6b6f-3fc2-420d-a978-64145b4816e9	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5-image-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
179a885d-2c6e-4680-b1fc-62abd0af94a6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4295fb21-485f-41f8-b96b-3b7fb0690e67	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5-nano	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0e1b988d-b521-4e72-96b3-5cd6370a4c5d	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8645ac3c-6332-4ab6-b07a-c1d9977e05bf	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
10cf7950-fde9-406b-ac25-5216d019d619	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.1-chat	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8fff1061-f813-4a27-9f8d-92762aacf6dd	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.1-codex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
934696d0-8928-4036-bde5-b8acd27890be	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.1-codex-max	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d0d5106c-bd9c-41dc-b122-4217128b464c	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.1-codex-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4744e7d2-0422-4cc1-af63-33b9e485c4ea	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
31847998-dbd4-429f-aefc-b50320c624a0	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.2-chat	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
59d22103-6f00-4c04-8dec-7bfd2a595685	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.2-codex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2035884d-c31c-4b01-9c5c-65e16e853f7a	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.2-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8379f70f-1e48-4d81-9007-3a0675b1cb1f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.3-chat	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7222e7e7-99ba-43cb-94c7-c1b15bbf3ea8	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.3-codex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
48046afe-bc72-4611-aa8d-81ed8ae7d286	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4f3e4434-bd7a-4395-be07-e7c9bdc5e8b6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.4-image-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e173d970-9ef4-4ac7-8562-137d5f269535	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.4-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f2675ad1-b4d1-4ce7-8287-cb068418586e	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.4-nano	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
940d9d46-24ae-4093-9301-f19200d52873	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.4-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2748a1e9-56f9-4d26-8e9f-576762d27ef7	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d8243d89-0faa-4c46-bb39-29dbb4a48191	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.5-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
99f018c9-ae11-421c-9bbe-8d946fbda6b9	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.6-luna	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
78a229ed-e18b-4991-b3dd-2e3e9ba4d46c	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.6-luna-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4b438256-591a-407a-be83-7887b947f5b3	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.6-sol	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
eacade82-3739-42cd-914e-f1047287e503	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.6-sol-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cbb93d46-6fc6-4bb8-9a29-68e11862d8e6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.6-terra	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0fd3ad35-28ee-4510-a5df-e4892f8443cf	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-5.6-terra-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b4564aee-681c-47ea-880d-6befe854292e	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-audio	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
291ca0f4-e780-4a6f-9572-5919283c8915	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-audio-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
22d33e8b-d496-4d99-b3a7-61b686122241	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-chat-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5343a7f7-9748-4e20-8794-ed76a23bbfa2	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-oss-120b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e18f5fe8-d4fd-40c3-a905-125628f94388	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-oss-20b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c4f3f864-a855-42d6-8c6d-7a7d2e609045	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/gpt-oss-safeguard-20b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
023cf213-c87d-4406-84f8-4a7e966d7b93	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/o1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c37dae2b-d2f6-427f-b626-949ed1c251f6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/o1-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a05af03d-05e1-4ef3-b3ef-d84ea3e58da8	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/o3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9b7db91c-f693-420b-949f-f4147016a132	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/o3-deep-research	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0a900775-f921-43f8-b1e3-f15953d23c83	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/o3-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c27f6c84-31b4-4c79-8a39-a626334cd5f6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/o3-mini-high	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4316f0d2-ad08-4824-8bf3-cc7d2dd580e5	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/o3-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
eec6184e-cf3b-41ef-a798-2a8a694e7c06	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/o4-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ac507471-70fd-4625-a94b-65fb94c32fe4	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/o4-mini-deep-research	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2bb9a771-7197-4cfd-b0ac-9209b487ab57	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openai/o4-mini-high	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
908e2b8b-41fe-4768-9e31-edc1a1ec1bcc	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openrouter/auto	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ea3cea04-783d-491e-bc3e-627a0281729d	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openrouter/bodybuilder	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
893e5317-c341-4f2b-8b2f-055d05da3770	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openrouter/free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
09ea73cd-b229-418f-9560-ad94f92a7668	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openrouter/fusion	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4178876e-43bb-41fd-92ec-aad0fae679e5	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/openrouter/pareto-code	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
09c1e93c-60cb-4f3d-b0bc-2695b8281200	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/perceptron/perceptron-mk1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
990e713a-33f2-4f11-bcf5-7ea149781760	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/perplexity/sonar	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d07a58d3-5434-4011-b29e-1b737d3c3cff	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/perplexity/sonar-deep-research	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
94ca2886-45e6-4adb-87a6-3cee2ff492a5	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/perplexity/sonar-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
004dc4b0-9094-4673-855c-938818810918	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/perplexity/sonar-pro-search	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
77792b63-4713-45ce-ac15-90603df94dc7	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/perplexity/sonar-reasoning-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3b62c615-fc9d-4b77-91c9-e68c6a1b209d	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/poolside/laguna-m.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7fef5fb8-1209-4fad-aa38-a9489d041783	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/poolside/laguna-m.1:free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4ece1a35-5378-4c3c-98bd-a0e6ec37de79	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/poolside/laguna-xs-2.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
81e45b9d-588d-433c-b9ca-aa51af58f6e8	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/poolside/laguna-xs-2.1:free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e0a71ccf-075f-4f8a-b451-53909d30fc15	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen-2.5-72b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5000a09d-78a9-4d50-80a0-999367b045d1	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen-2.5-7b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9f5adb37-4cac-4a9b-b1a9-fb8cfac5cf12	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen-2.5-coder-32b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e083d3a1-c7cb-492e-8837-78f496e18cf1	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen-plus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3f2138b8-e4de-4999-a636-9ac380d93f02	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen-plus-2025-07-28	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
414cc66a-7f50-406d-ba14-f7cbd6fb777e	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen-plus-2025-07-28:thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f82f9840-2ba9-49af-af1d-ec46ef58a292	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen2.5-vl-72b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c8583d9d-047e-4409-bcb6-8af5fb7b9729	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-14b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1c98aa91-3447-4110-9d73-1049b331da82	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-235b-a22b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
717a2437-3ea4-439d-8005-58820edcbce8	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-235b-a22b-2507	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
40201a1e-8541-4dd3-b92a-c93c64872823	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-235b-a22b-thinking-2507	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
60435e09-c23f-4032-b686-331bef2d53ef	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-30b-a3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f305b9e0-9907-49e8-99bd-82081405d09d	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-30b-a3b-instruct-2507	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
968b4b47-473b-457d-95f7-48fd379365cc	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-30b-a3b-thinking-2507	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bf61b4d3-0858-4332-bdb2-3fff51f65a4a	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-32b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5e372916-beab-4028-ae21-b0b6bc24391c	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-8b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
17739dab-5f48-44cf-a5af-95806cb3bd18	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-coder	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
791a21cf-09a2-466b-aa45-9f604c4872d4	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-coder-30b-a3b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5b30458b-68ed-43b8-af6c-fa68b84b9d20	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-coder-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a75486eb-7ae9-4e18-b763-8889bd3a328b	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-coder-next	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cd0373ca-5bf7-4f03-8692-b03eaa8bf829	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-coder-plus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
08863f6e-16fc-4370-853a-04bfa79cd9fd	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-max	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2e421048-12e1-45d8-9809-19e914207210	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-max-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
54b4151b-1017-47a0-ab37-5520deec8268	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-next-80b-a3b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9a7abe3d-c48c-498f-9ebe-82092bc47e9b	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-next-80b-a3b-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
26490c8f-7cf2-4e1f-8350-f2213fdbf4f0	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-vl-235b-a22b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
09456d82-04d8-4ffb-b44c-fb96701c06d4	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-vl-235b-a22b-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1b22cb2d-b358-4a59-a502-58a43cbe2a26	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-vl-30b-a3b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
87f6b7e6-401d-41cc-bd9d-688cea8a2405	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-vl-30b-a3b-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b45f49ca-8042-4823-b49d-752f8670f9d8	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-vl-32b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2ed0050e-224a-4611-b76f-9a11cbffd58f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-vl-8b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
66257c1b-88d1-4726-9e77-64ee4f7c3b7b	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3-vl-8b-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1b319298-d4d4-4747-adf2-79cb5a977053	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.5-122b-a10b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1cfa1bfc-de2a-4dde-ad0e-538a201e4d7c	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.5-27b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
aee9a699-8d31-44fe-aa53-1bbe3c4fdd31	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.5-35b-a3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
02891ce8-24ca-4faa-ab26-8e54859ef9c3	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.5-397b-a17b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b05c4400-b1b0-4cf6-9b60-e89187b80c70	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.5-9b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b017a577-b2e1-45db-9291-e291fde8b9c1	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.5-flash-02-23	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2fc7f714-73e7-473a-adf1-ce31bc7b1a3e	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.5-plus-02-15	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4ae6dc40-2375-4e3b-b42c-89c1f5aedd33	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.5-plus-20260420	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b156ffec-878e-40b1-9cfd-39788640639f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.6-27b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ae4a736d-3ef5-48c6-a017-223bfcc83a49	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.6-35b-a3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d648903d-cc65-44c1-8bde-41ae70a8304f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.6-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
356d9df7-03e2-4ef4-b965-fb5be2799c22	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.6-max-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6bd8697c-a536-4319-9fa5-16792d8ab668	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.6-plus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1d0da817-a266-4b74-b4d5-5e4341561aaf	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.7-max	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cd982bab-75b0-4715-9b40-b53439cdd77e	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/qwen/qwen3.7-plus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bff6284f-59a1-4f79-b7cf-f275c5a19cc0	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/rekaai/reka-edge	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
edc271b1-0d9b-4207-9cea-ca16de308d6a	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/rekaai/reka-flash-3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e9bbc001-1733-4fd9-a731-605bbc8f7404	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/relace/relace-apply-3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ade882cd-e080-4a0d-9009-b7766f6bf3a3	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/relace/relace-search	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bcc685cb-03a7-418e-903c-59d29a582c44	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/sao10k/l3-lunaris-8b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
af659a43-1ec4-4e06-ab2a-fc3ecfe288bf	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/sao10k/l3.1-euryale-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6d7db213-b02a-4811-ad2d-309abb5ba3c1	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/sao10k/l3.3-euryale-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7ee5f996-3780-485b-94d5-efce874c59be	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/stealth/claude-opus-4.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b0746d56-2748-4409-b922-5df3f1102f63	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/stealth/claude-opus-4.7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e46ef7bb-5a22-48c3-8df1-14c946a8f760	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/stealth/claude-opus-4.8	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d57ae066-5d17-4153-b19b-a1c4768c4662	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/stealth/claude-sonnet-4.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a438c0eb-c798-41b6-8998-e55c1b6ab924	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/stealth/qwen3.6-plus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2ba88b54-cf22-4906-8d81-7dae49a5437e	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/stepfun/step-3.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fb782e0a-a6cc-4634-bf9c-3c44767967c9	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/stepfun/step-3.7-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
544f88f6-6717-429e-be7a-fdf0e8037ff1	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/stepfun/step-3.7-flash:free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2690f210-faa4-4915-94bb-3f115eced007	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/tencent/hunyuan-a13b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f9fd8125-ce7c-4e1c-9f6f-99fcf448475f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/tencent/hy3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8e5249e3-d690-406d-ba92-c11fe5080ac7	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/tencent/hy3-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0855357c-5ae5-4e4a-af32-fa0f3785d473	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/tencent/hy3:free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8d8295b9-fb48-4ece-875b-ea3cb089c7a9	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/thedrummer/cydonia-24b-v4.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
93684729-f412-4d3a-87fa-4d37233ecc2b	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/thedrummer/rocinante-12b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b75d9b8c-b913-41dd-b104-c5d019309c8b	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/thedrummer/skyfall-36b-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
824d4c2d-20ed-41d9-97b7-e57e1fe01a64	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/thedrummer/unslopnemo-12b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4acbb670-5203-41fa-a342-0360970ccef7	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/undi95/remm-slerp-l2-13b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5afded4d-cc34-44b8-a983-9869cf009f05	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/upstage/solar-pro-3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1bfbfb63-1afa-49a5-adb7-6725d01a9200	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/writer/palmyra-x5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2e3b3e67-6181-4e2f-acd2-941d8888cb99	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/x-ai/grok-4.20	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
aa643642-3e6c-4081-acae-b6861e4ec6be	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/x-ai/grok-4.20-multi-agent	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b9fa29d4-9387-4f63-83ad-13d96e1889b6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/x-ai/grok-4.3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e6da5c83-a74a-4b89-b131-b8010ca23a7e	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/x-ai/grok-build-0.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ccb8de24-39f3-468a-a52c-493cb53a3f08	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/xiaomi/mimo-v2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fe3ffe90-d1f5-4b64-a30e-dbe1be7e14c4	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/xiaomi/mimo-v2.5-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
764dec4c-1be6-492d-b07f-80bb633aa563	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/z-ai/glm-4.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
45a01609-a4a9-4e97-8b3f-fe00e4e16874	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/z-ai/glm-4.5-air	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
88bec2db-c89f-4146-90a4-a8c7a69c05d4	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/z-ai/glm-4.5v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9f3f5930-bede-4e46-950e-9dd724d29fb7	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/z-ai/glm-4.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4065ec04-b54b-488a-afaf-67a5fe8df8d9	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/z-ai/glm-4.6v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9ddd5060-4428-4cd9-b66e-41bfeba20ba6	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/z-ai/glm-4.7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
000f28b3-af33-4b3a-9229-2bf05520192f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/z-ai/glm-4.7-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0f1a4f9b-fb4a-4c02-a7dd-c80969da6075	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/z-ai/glm-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a162df6a-82c7-4f32-9a4e-86e1c26ae9a0	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/z-ai/glm-5-turbo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cdfbf2fb-bff9-43db-bab0-53e57127bc5f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/z-ai/glm-5.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f58f8552-7552-4711-b54b-b3ddf94a920f	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/z-ai/glm-5.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c3fef732-121f-48d1-8018-f0be1b2d92d4	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/z-ai/glm-5v-turbo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5fe5b9e0-b3fc-4506-9499-19e5b8e9d0e7	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/~anthropic/claude-fable-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a1ea0a36-532c-4834-bd9b-4e00236d4478	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/~anthropic/claude-haiku-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8146de8c-2e54-427e-99f9-c91a168a9ffb	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/~anthropic/claude-opus-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
895bc0ec-7bf6-4513-b0a7-8e3ac437ca17	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/~anthropic/claude-sonnet-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e60b1359-bbf5-4e63-a47a-049eac572622	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/~google/gemini-flash-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
af771cd1-035d-4845-b117-96274a0c4059	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/~google/gemini-pro-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
15e221d7-d144-4cbb-b470-b7deb751e00a	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/~moonshotai/kimi-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
64072643-1f9e-41df-811b-7a87643b6e8d	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/~openai/gpt-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2c9e120c-334b-43f8-a25a-5173daa1a90d	e383c6da-a54b-4224-986e-deee71353d2f	kilo-code/~openai/gpt-mini-latest	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0f70fc51-de17-49ef-8714-e52b4994514d	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/01-ai/yi-large	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c8dd596d-5524-41d3-a88d-8fafebb79d0e	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/abacusai/dracarys-llama-3.1-70b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4d322255-9c44-443d-a77c-7cafad793270	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/adept/fuyu-8b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5f63e4cf-ebdc-43c0-9d43-01856dd8aab7	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/ai21labs/jamba-1.5-large-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bb4ca4c3-e50f-4b9c-8c97-998b09779b05	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/aisingapore/sea-lion-7b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
684e4e0c-b131-4a09-9e8e-a955fa8bdc07	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/baai/bge-m3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3ac99ad7-1c6d-4040-9002-142c6b5c2e97	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/bigcode/starcoder2-15b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1371a1ea-1288-4fea-9693-646d6e7e5a59	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/bytedance/seed-oss-36b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d13bab70-481f-4be0-8527-cad423d75bdf	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/databricks/dbrx-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d337664c-b61e-4a65-82f2-f93935f9b38f	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/deepseek-ai/deepseek-coder-6.7b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
68477d69-7f0c-427d-8c08-5931fcadd408	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/deepseek-ai/deepseek-v4-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2b1aa9ea-7930-482f-8da3-af2caca956ee	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/deepseek-ai/deepseek-v4-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
48e16e25-45af-42e9-b3a2-55dd0736cb83	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/google/codegemma-1.1-7b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2a7a19cb-54ea-4bd7-a64d-b52ccedad051	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/google/codegemma-7b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
241c4f59-0f1b-4b2b-8b48-9a349672e8da	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/google/deplot	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
17e51097-dbbe-4c6f-9a7b-5db5ad552878	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/google/diffusiongemma-26b-a4b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
95a39fde-c41e-4cdd-8add-99ed9b415256	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/google/gemma-2-2b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7e84f0dd-8cb2-4254-908e-f52a7743efa0	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/google/gemma-2b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a4cdbdfa-e9f9-4d9a-9a2e-5cb3c9e455dc	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/google/gemma-3-12b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
89ac313a-4f49-48ae-b78a-dfed723224bb	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/google/gemma-3-4b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
549fa2d1-4c99-42de-b948-6c3925ae79df	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/google/gemma-3n-e2b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
83a4bad6-2f8b-452a-987d-94a3e491990b	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/google/gemma-3n-e4b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1eb021c0-05fe-428b-b8b9-134d13299149	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/google/gemma-4-31b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4a9458a1-6fbc-468c-a057-3a648f9a3eee	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/google/recurrentgemma-2b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f91c5405-d6a7-437d-b6c8-fa42cec5c188	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/ibm/granite-3.0-3b-a800m-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ca4dc207-3891-471b-af77-303dd2f5afdd	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/ibm/granite-3.0-8b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3b30c695-0f5f-46e3-b34f-657f6441cbcf	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/ibm/granite-34b-code-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f14b48f5-3239-4fd1-a6e2-7d29934a2da6	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/ibm/granite-8b-code-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c0325827-9323-492a-9631-2e8dd1dc1fdf	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/meta/codellama-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
10b4f6e2-ba25-4c34-89b5-7ede6774da4c	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/meta/llama-3.1-70b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1a1bbee2-311e-4020-abf0-f13a7b6acf44	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/meta/llama-3.1-8b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5aa036a0-dcd0-42bf-8bd1-6878eeb345e1	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/meta/llama-3.2-11b-vision-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
765f1dbc-1f00-4de2-94ae-8c20c5a8182a	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/meta/llama-3.2-1b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bc5b3306-50b3-43fc-a286-d93e59a91da9	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/meta/llama-3.2-3b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c140a95a-3622-41cb-8a6c-a8aa9aaaef9f	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/meta/llama-3.2-90b-vision-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
56e8eeba-88e6-4d5c-96c2-1a9ee3244e3f	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/meta/llama-3.3-70b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
288632df-abec-4913-bc6e-34c52c14f52b	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/meta/llama-4-maverick-17b-128e-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
03016537-7b3a-49d7-a94e-c6b7058c2c0f	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/meta/llama-guard-4-12b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5a19d987-e215-4b38-8ff8-6771ce3d9bc9	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/meta/llama2-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
84981d76-6ca5-4c72-8905-74fa216b8e2c	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/microsoft/kosmos-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5b8c2cf0-e88e-47ce-a6f8-9c1f319b4659	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/microsoft/phi-3-vision-128k-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d55bb196-b1b6-4df4-966c-b885eca8705a	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/microsoft/phi-3.5-moe-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
122dc0bd-cdc6-48b4-b633-d30327839d14	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/minimaxai/minimax-m2.7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d8c3cba8-eba0-4c7b-9e04-ae2249a10893	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/minimaxai/minimax-m3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
81e476a0-795f-4e45-9599-9be66f147f4c	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/mistralai/codestral-22b-instruct-v0.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5e476157-5bbf-4c4b-929b-3aaedf06a0bf	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/mistralai/ministral-14b-instruct-2512	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b8661c74-51fa-49c4-b513-6b202c5c4b59	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/mistralai/mistral-7b-instruct-v0.3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
530739eb-8fe7-44db-997a-830d6d50b3df	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/mistralai/mistral-large	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cc54dae8-7db0-4364-aa85-4b67f73b93db	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/mistralai/mistral-large-2-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a6d38848-11e2-4ef2-b82f-0b76cac62177	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/mistralai/mistral-large-3-675b-instruct-2512	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
574cd682-b387-4b49-ab8e-acdcfcceaf06	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/mistralai/mistral-medium-3.5-128b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a4b4b4a0-77ec-4c83-9dfe-c7978d618a0c	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/mistralai/mistral-nemotron	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7bc87d8f-c08b-48db-9bf9-900fc0b0c1b7	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/mistralai/mistral-small-4-119b-2603	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7507579c-339a-403d-bc5c-1a74f6d0bd3e	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/mistralai/mixtral-8x22b-v0.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4bc0ed96-8e49-40de-a3a0-cec1fb974ab3	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/mistralai/mixtral-8x7b-instruct-v0.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b773d7ac-ff39-43fc-b4ef-b16da3718d24	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/moonshotai/kimi-k2.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5ed2d264-0536-4509-9951-f2ae476c06f9	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nv-mistralai/mistral-nemo-12b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
899fde1d-46c5-4333-98f6-3a49a963e3b9	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/ai-synthetic-video-detector	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4ce956f3-cfe5-4cdc-840a-8c59ef27782d	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/cosmos-reason2-8b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c628db83-e374-4951-a92e-c2a41c355db7	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/embed-qa-4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c619bed8-ff4d-4977-a221-9c04393a7628	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/gliner-pii	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
53b89092-55c0-4b5f-bad1-ef8183e6e261	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/ising-calibration-1-35b-a3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6b95c033-4db1-47a3-a26f-ac72e362c38f	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-3.1-nemoguard-8b-content-safety	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9bb6af20-7366-4008-8303-e8154637d63c	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-3.1-nemoguard-8b-topic-control	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
02281065-8e1e-4075-be70-619370d7bc72	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-3.1-nemotron-51b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b7ef8a4f-7ba3-443d-98d6-4746660efdd6	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-3.1-nemotron-70b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
830d957a-1dc4-4825-84d6-b490888714a0	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-3.1-nemotron-nano-8b-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0c2804af-1365-464e-b168-b0fe4e0e9a29	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-3.1-nemotron-nano-vl-8b-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
014c0cc7-8867-4b1c-83f9-3830daa6cf1e	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-3.1-nemotron-safety-guard-8b-v3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3b66175b-74df-41db-a6b0-d7bca88b3183	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-3.1-nemotron-ultra-253b-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
61fef060-3603-4986-bf00-b4595cbe5ce2	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8774a05b-82e7-4257-b86e-d06c049bfe80	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-3.2-nv-embedqa-1b-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2a8d990d-3555-495c-b1e1-fe2dc0166216	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-3.3-nemotron-super-49b-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1bc4acb4-f50b-475d-9e54-18c7337af8db	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-3.3-nemotron-super-49b-v1.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
03f3844f-0316-4a31-ad75-821aefa25ab5	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-nemotron-embed-1b-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c38bf5e4-cff9-44c1-bc74-99e468ea22ca	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama-nemotron-embed-vl-1b-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
70689ee1-a739-437c-bb70-f4a6f08427ee	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/llama3-chatqa-1.5-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f8192e0a-0ba2-463e-85c2-88a907769c19	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/mistral-nemo-minitron-8b-8k-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a0f93c11-a6fa-4326-8721-e73a2188d455	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nemoretriever-parse	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d7152947-bef8-4d04-a963-033e79f20e6b	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nemotron-3-nano-30b-a3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4f458929-b056-42e8-8f8d-096d9ed50970	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
14d8e3d4-4fa1-4c3c-a687-84f25fbffac5	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nemotron-3-super-120b-a12b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
12a7141c-3423-40e4-8ef7-6dd3bb7ad4ef	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nemotron-3-ultra-550b-a55b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1e79bd45-f860-4cac-9632-bd236810fd08	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nemotron-3.5-content-safety	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5c836d7a-1097-46a7-b958-d136969a9cf3	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nemotron-4-340b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f35d4d70-baf8-406c-b4a5-cac6822975e6	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nemotron-4-340b-reward	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ed801f6c-c175-4251-bc71-1d9dfcf6b983	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nemotron-mini-4b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c2b286f0-3995-431f-9f4b-2ddc2edbcf08	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nemotron-nano-12b-v2-vl	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
53391fd8-24ed-4130-bfbe-01ac923c7fe8	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nemotron-nano-3-30b-a3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b98074b4-dc3c-40b0-aba8-b75fbc3f2ae0	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nemotron-parse	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3de1051d-3966-44e3-9205-db9adaa6d28e	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/neva-22b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1a2ff4c6-45b4-4a02-83b7-be3bfbd20a50	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nv-embed-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8ca3677f-e198-46c4-950b-c2ad7b736926	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nv-embedcode-7b-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
04089a39-7e9a-437f-a9bd-dcf0a8e6d6a6	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nv-embedqa-e5-v5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0508cede-5c5a-40cb-996b-60f8ed1cb4b4	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nv-embedqa-mistral-7b-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5073c9ba-fdf4-4482-99b5-342f6fbedd18	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nvclip	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bdad50ac-d68b-4978-950f-e5f733f5b764	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/nvidia-nemotron-nano-9b-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
baaba2f1-470f-4b6d-85af-e5c7ad04a284	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/riva-translate-4b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2722bcb8-60cd-486c-a5e4-3e4ab6ce78fa	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/riva-translate-4b-instruct-v1.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cad14d21-88d2-4292-9682-2dd14275d455	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/nvidia/vila	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
61e0b44c-e3c2-47fa-a99c-1f307e63d113	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/openai/gpt-oss-120b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b4727565-ecd8-496c-a54a-6c923de62e61	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/openai/gpt-oss-20b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9ec9cc5f-abe6-4939-af5f-99207be67789	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/qwen/qwen3-next-80b-a3b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e0d53854-40b6-4de9-97aa-a8b47e4d87f3	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/qwen/qwen3.5-122b-a10b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
38b236bf-a962-42e9-92b8-bd259d607063	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/qwen/qwen3.5-397b-a17b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e55e3095-50ff-4fe1-828c-2c99bcf3edc4	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/sarvamai/sarvam-m	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2e011f6e-d6d5-4048-970b-27d7f187a715	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/snowflake/arctic-embed-l	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e242f81e-214b-4c86-8e7a-2f65194c2d43	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/stepfun-ai/step-3.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3adea2ba-bb20-4a38-8e1d-1c64342c0f47	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/stepfun-ai/step-3.7-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d1d90292-2ab4-43ba-8a5d-b2c8b6103580	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/upstage/solar-10.7b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e8cdce34-ea07-40b5-910c-807c692af79a	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/writer/palmyra-creative-122b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
08fd9983-c630-4dab-9fa6-7d98536d1168	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/writer/palmyra-fin-70b-32k	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ce770d47-59c2-4de0-8e91-073d2bcefab8	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/writer/palmyra-med-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
edd6123e-9d6e-4291-a3e3-7a17cd30c691	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/writer/palmyra-med-70b-32k	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8e6edd1e-46a1-471d-8f91-206d1d0b3ef5	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/z-ai/glm-5.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4d173336-f6ba-4623-8036-b3299979bfa7	e383c6da-a54b-4224-986e-deee71353d2f	nim-think/zyphra/zamba2-7b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ec503087-acbb-4795-a21b-58ad494ddc22	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/01-ai/yi-large	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1121727d-a5f3-4706-82d5-7b0b5b2964ad	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/abacusai/dracarys-llama-3.1-70b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5e958d10-3d16-41dc-8cfa-95bb14d79b10	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/adept/fuyu-8b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fbde8833-f0ec-40ed-89ba-ba047af11f1e	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/ai21labs/jamba-1.5-large-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4a1f60b6-ccd8-4f54-88a3-0df7f7755bf9	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/aisingapore/sea-lion-7b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b2ee0142-df6f-446d-bb01-592df70ab77f	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/baai/bge-m3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bb92ede9-506e-45e3-aa35-22353ba33133	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/bigcode/starcoder2-15b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3aa87cd0-ef1a-475a-8d1e-df32f9bf16b6	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/bytedance/seed-oss-36b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
432e2709-4506-4abb-8609-82cc4a834426	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/databricks/dbrx-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f2ef508e-bfba-4914-8e11-056f83889f47	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/deepseek-ai/deepseek-coder-6.7b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0223d017-f6b3-4b65-847d-fd8a8e1d63db	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/deepseek-ai/deepseek-v4-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bb2b23dc-6ced-4cbd-b2c4-480895e074a6	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/deepseek-ai/deepseek-v4-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
22204f63-3bd3-4cad-91af-54faf09ef376	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/google/codegemma-1.1-7b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d76902ce-3560-4ab9-ad9d-801d5c6b157b	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/google/codegemma-7b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ab268f3d-c624-4052-b93e-036e0b1cee30	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/google/deplot	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a0864937-1fc0-41c2-b556-10af77130ac8	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/google/diffusiongemma-26b-a4b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
828b08cb-5e8a-4b38-a286-ccd28d1337f7	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/google/gemma-2-2b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e01c66dc-8870-4b22-b76f-cdcbe95629d5	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/google/gemma-2b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0754b66f-0fdb-4990-b7c8-29a110967268	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/google/gemma-3-12b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fd38efb1-1c8d-41bc-889d-4dbd60c331ea	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/google/gemma-3-4b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
14a465c8-ada1-400c-a9a7-cc27d9a60b87	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/google/gemma-3n-e2b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
254be016-988d-40db-8679-95b7b43e7802	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/google/gemma-3n-e4b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
dda7b684-fcca-439d-900b-cfb4bff347ff	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/google/gemma-4-31b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
49bbbb7c-192e-4302-aea4-e1960ccbee8f	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/google/recurrentgemma-2b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4bbf8d3f-8606-4f35-b8f0-730fd60bb493	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/ibm/granite-3.0-3b-a800m-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
06c8bcb6-c69d-45e3-9bd8-8a9d4da87f7b	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/ibm/granite-3.0-8b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f6bc044a-1cff-4ebe-bc70-e02d1358a354	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/ibm/granite-34b-code-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9f8ca66e-d43f-4fd4-8a47-d9d1eb97cf33	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/ibm/granite-8b-code-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5486efa3-a637-4b68-a54d-be74428c3105	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/meta/codellama-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
88d216bd-e4d8-4333-b82d-30fcbff28fbc	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/meta/llama-3.1-70b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ebadc5dc-0647-4a6b-ad65-354a5adf125e	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/meta/llama-3.1-8b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c3e28187-4f18-4b1c-95e3-93f3b3d19b80	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/meta/llama-3.2-11b-vision-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
81f1a07a-91ae-413a-9bff-bca519ad1888	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/meta/llama-3.2-1b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2918bbcd-f35f-423f-8438-5202deafb05f	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/meta/llama-3.2-3b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
17b394ec-e1c5-4c1f-a205-d368eaf56ec3	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/meta/llama-3.2-90b-vision-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1a80c38e-eeea-4dc2-add4-b669b2298468	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/meta/llama-3.3-70b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3f208a6a-889b-4e34-b92d-10fe4c2f5aa0	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/meta/llama-4-maverick-17b-128e-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d7851e2b-7367-46d2-a7ed-48cc6a92ba56	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/meta/llama-guard-4-12b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4296d21d-4922-4bb5-a89a-dd8d58108c9f	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/meta/llama2-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bd3f733b-5fdb-41f2-95f3-4521fd39e508	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/microsoft/kosmos-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c35a86ca-d5c5-4c49-a9f0-5a57df97ac9c	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/microsoft/phi-3-vision-128k-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
52c0ab21-431b-404d-a583-ff3bc6142abb	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/microsoft/phi-3.5-moe-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
abdf7334-838b-4c40-bb26-eb62897281c2	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/minimaxai/minimax-m2.7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9c5dbf41-2ec0-48e7-9829-f22ba3f82ccd	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/minimaxai/minimax-m3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bd98b227-d1dd-4f46-b192-ede0ea209aaf	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/mistralai/codestral-22b-instruct-v0.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f17fcb6b-6c4a-43dd-a1c9-d6bfc7054648	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/mistralai/ministral-14b-instruct-2512	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9f1bde78-0fa5-4c7f-8e76-703d4bcfaa9e	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/mistralai/mistral-7b-instruct-v0.3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ac153e9e-cb5a-4e63-b938-b71406921243	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/mistralai/mistral-large	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4a378417-98c4-46bc-aea8-4177d42d3a65	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/mistralai/mistral-large-2-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7de47b9a-6a34-4185-83b2-664d585e31db	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/mistralai/mistral-large-3-675b-instruct-2512	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
893f205f-1d94-4f61-9b98-b3350909679b	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/mistralai/mistral-medium-3.5-128b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4660d2ef-8ba4-44d9-9114-18b1343b50cb	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/mistralai/mistral-nemotron	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
be4e714e-04e6-4b00-ace2-63c26bb28f5c	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/mistralai/mistral-small-4-119b-2603	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cd825d2e-d339-45b0-8938-b9ecf0ba3f69	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/mistralai/mixtral-8x22b-v0.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2fcef491-cd2f-448c-b221-3f9e5bb83a84	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/mistralai/mixtral-8x7b-instruct-v0.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
821f4260-5fa3-481f-abfe-df408a3e5b4e	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/moonshotai/kimi-k2.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
87a4f2c4-e73a-402f-b849-b45b549d6da9	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nv-mistralai/mistral-nemo-12b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d42018df-74c0-42ee-bf87-e36d7d359d65	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/ai-synthetic-video-detector	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
136196fb-669b-4ff1-a4d4-1c5237bf459a	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/cosmos-reason2-8b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ba1a11a7-9551-4643-8f6a-198e1d67e3a6	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/embed-qa-4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f8aacd50-d085-4b5d-9ffb-5d48cf8bf1f2	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/gliner-pii	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
85302c1b-6ede-4bc0-b889-d752c12b8a81	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/ising-calibration-1-35b-a3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a446cb46-a757-46a2-a17d-afcb0e2eab5e	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-3.1-nemoguard-8b-content-safety	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a75d34e8-2fc2-4c12-9185-17c449d37149	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-3.1-nemoguard-8b-topic-control	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e10f22e2-1624-4358-b306-ba57d04de4dd	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-3.1-nemotron-51b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6176ccef-8cab-41b1-a971-f22d9b5a4f48	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-3.1-nemotron-70b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a2b9ae1d-7c34-4887-8c53-3461749beaab	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-3.1-nemotron-nano-8b-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ed4b90ea-468f-4cf0-aa50-f2c44aa8b1a4	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-3.1-nemotron-nano-vl-8b-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a27edc17-b8ad-4991-bdb9-d95c7a66d924	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-3.1-nemotron-safety-guard-8b-v3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
dccdeb52-f227-47e4-ac36-386e5dc9162b	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-3.1-nemotron-ultra-253b-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d8e60778-32f7-4116-a565-d842ce709856	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
429c9069-6369-4433-a139-43ee18cc2146	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-3.2-nv-embedqa-1b-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
416a190b-463a-48f4-8440-d35fb028d0ed	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-3.3-nemotron-super-49b-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2cea777e-6b87-4465-ad25-63ce4015fdc6	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-3.3-nemotron-super-49b-v1.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a84381e6-c21c-40d9-a94f-846b5ef78e45	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-nemotron-embed-1b-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
45138cbe-97ab-4dd9-af4c-26726af1ad54	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama-nemotron-embed-vl-1b-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4f2d160d-a873-488f-a7f7-a01cac46913f	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/llama3-chatqa-1.5-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e593b3d3-75e5-439c-9a63-e427aca85bf2	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/mistral-nemo-minitron-8b-8k-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a9221b88-6a57-48eb-a549-75aceea6d5fe	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nemoretriever-parse	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0507e94a-b55c-4b33-844f-4f752561353a	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nemotron-3-nano-30b-a3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7205e1c8-c599-4193-a0cd-931e81c73356	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
18eb8b3b-967e-4438-83ba-662fe62b3303	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nemotron-3-super-120b-a12b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
96e02a6e-5771-4fe5-be24-649fe03ccb91	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nemotron-3-ultra-550b-a55b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c12cbb6c-2eeb-447c-be53-6feec360ddac	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nemotron-3.5-content-safety	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d1bbaee4-db2f-4f26-8da4-84ba5887472c	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nemotron-4-340b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7395b16d-563d-4fd5-885a-5943fe8f7183	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nemotron-4-340b-reward	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
285aaead-134f-4100-a156-010347f773db	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nemotron-mini-4b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
33227ab6-527a-4172-9c8d-d9c796dfa143	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nemotron-nano-12b-v2-vl	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f49e7bdb-f88d-4d98-8bef-193eae9d0a16	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nemotron-nano-3-30b-a3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0a9b8e82-d990-48e1-a8d0-b870fc109eea	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nemotron-parse	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f20dca91-4685-4ca3-80d9-b5ed5fb987bf	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/neva-22b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
54e5b806-c469-4894-af83-ec0763058bdd	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nv-embed-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4c720fbf-56f2-439c-abbd-3d7058260947	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nv-embedcode-7b-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6b70c2e8-e2b6-4216-a7ae-63c2ec16d47e	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nv-embedqa-e5-v5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
14b14c35-e2f0-41b6-be78-c2a465d7e6c3	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nv-embedqa-mistral-7b-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b16303c1-fac0-46c1-8d89-ee9cc0e57dc5	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nvclip	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3fb1e072-cc5d-4f75-8540-ebd6afb3da5a	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/nvidia-nemotron-nano-9b-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c52aabde-58de-4eeb-b461-6aff2c4afbbe	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/riva-translate-4b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6551f588-0e4e-453a-bf73-3e7240d1d05b	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/riva-translate-4b-instruct-v1.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f65168bd-a7c0-491b-a62b-6862dfb2a611	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/nvidia/vila	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f5db5b0a-e269-408a-a680-d5714b28f666	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/openai/gpt-oss-120b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3f0569db-8895-44f2-84df-2ceecb0764d4	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/openai/gpt-oss-20b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1ec9aae5-4f11-402f-86df-be3924c0f48e	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/qwen/qwen3-next-80b-a3b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0ed39745-40d8-4aaa-8a58-49d5cb8cc003	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/qwen/qwen3.5-122b-a10b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4d6cd146-a890-417b-9e1d-f8ca89324efa	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/qwen/qwen3.5-397b-a17b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2fd8335c-21a7-48ed-b353-b2e473af79ea	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/sarvamai/sarvam-m	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
56d58f22-dcd9-490e-a2c6-ffdf07c8be35	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/snowflake/arctic-embed-l	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5ee287a1-6a68-4fef-88a5-1c0d2cb300f1	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/stepfun-ai/step-3.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
47cb7b7e-edb5-4e90-a632-932b77adcd3f	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/stepfun-ai/step-3.7-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8968b85c-90bd-4e1c-84fe-e6e1c7013951	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/upstage/solar-10.7b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d69c55d1-9127-4e57-b2a2-7928d78935aa	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/writer/palmyra-creative-122b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
899a22a2-a995-46ad-99b1-5fde7e77c50f	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/writer/palmyra-fin-70b-32k	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c10f3895-3624-40db-9a9b-829014a9847c	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/writer/palmyra-med-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8724fd88-817b-412f-9a18-268655eaa0ff	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/writer/palmyra-med-70b-32k	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5fc709ea-40e8-4ee7-9dc1-aee800e7966a	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/z-ai/glm-5.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f53b70b2-f0f7-4405-8a2e-a91de5530a7f	e383c6da-a54b-4224-986e-deee71353d2f	NVIDIA NIM/zyphra/zamba2-7b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3c5f031c-3038-4d60-9dad-ce5711152476	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/big-pickle	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3056313e-1189-447f-862e-0242826fc16b	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/claude-fable-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d7c2c644-7873-40f8-8f0a-a7e8097451e9	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/claude-haiku-4-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
53f1d146-12ad-4542-a8f6-d3c41f42c7c5	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/claude-opus-4-1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
babddbc5-c317-4201-bb61-278658642728	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/claude-opus-4-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
41897ab7-e502-48d8-86f7-006b663f4922	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/claude-opus-4-6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
79e46d91-2f0c-44de-88e4-b186b124f873	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/claude-opus-4-7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e16d735a-651a-4b85-a638-9167fec94494	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/claude-opus-4-8	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1d013581-435f-4f90-8b10-a6114efe96e2	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/claude-sonnet-4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2b090a39-8231-4460-bce3-d95bb12881cc	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/claude-sonnet-4-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5f1a980b-1d53-440f-ab48-9c1509372b24	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/claude-sonnet-4-6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b10cd2e5-199f-416e-b63a-6ee14dc90fc4	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/claude-sonnet-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5328e8cd-030b-4509-89ac-dc91c0106f0b	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/deepseek-v4-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
38f41c21-4e95-4280-b824-b790837ebdc7	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/deepseek-v4-flash-free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
95838830-4d98-47ea-9847-3959cb0e8d39	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/deepseek-v4-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2d5093c8-3cd1-47f3-92e8-108aeb75ee5a	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gemini-3-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7d0cc7ae-8454-4b54-8ea2-c17f118f303a	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gemini-3.1-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5c9f58e8-0724-4f21-bfc9-016fa85131e8	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gemini-3.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2529e64d-8f6b-4ab2-b09f-8f37dd00741a	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/glm-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5baa654d-b3cb-4150-980b-0ca9849656fa	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/glm-5.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
aab3fe8c-1d8d-40bc-8d9b-f93c1ebe7775	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/glm-5.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
08242b62-14a4-4b75-b2bb-6f347595a994	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
48898897-a1d4-4581-996f-762f828d1786	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5-codex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
80b1498c-97a1-45c2-912d-8baf5c4b1174	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5-nano	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
52e66b7d-6dd2-4981-a5fe-049c5a9258bc	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
12778d13-e4e6-4c64-acde-808dff95a394	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.1-codex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
50616dc0-a4eb-4104-9c50-08672078eee0	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.1-codex-max	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7e4e5dce-55f9-4989-84e9-a62b524184f5	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.1-codex-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
69ee70e7-5eaf-4393-8ef6-b452da158914	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
98dea77b-2e64-46a0-aefe-8d5858fda58b	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.2-codex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b6d20c0d-572a-4ac9-adaa-c6c8cc46d499	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.3-codex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c4bd7f47-02ca-4aac-aaf6-9e8953303d6d	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.3-codex-spark	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a6075092-89f0-4447-a82a-05b3f5541f25	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b48b8588-bb48-4adc-a61c-ee8d175a2e42	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.4-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4d0090ac-ad71-490e-b387-5b892dd4fa7f	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.4-nano	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
57bfc0da-b9ea-4af8-85d0-324919669abe	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.4-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
22793d04-e03e-4245-bea5-2054d06e8616	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d2b6d640-8d53-41bd-b3c9-554bc79d9fec	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.5-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
28bd1611-105e-47a4-8830-da75666ee11d	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.6-luna	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c4f1b90b-f581-499b-aa14-8a3047e745a7	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.6-sol	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4bd6ca09-e47d-4b68-8099-1a8e62320bda	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/gpt-5.6-terra	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d6ddc3f7-2552-4ebb-b262-7dd1f6be1fe3	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/grok-4.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2c76a6bc-8f58-4eab-8c1e-c117f7dfcdc3	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/grok-build-0.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
92074476-92dd-41b0-9640-b56a53e6d2a6	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/hy3-free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9433912e-c9af-4919-8254-092cb94b8775	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/kimi-k2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
be24351f-25f8-4f3c-90c0-415019f1f3cd	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/kimi-k2.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d46369ec-6e00-46a5-a7ab-32fa788beed6	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/kimi-k2.7-code	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
63cd11e3-aa68-469d-aa8a-6c92d77a4c30	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/mimo-v2.5-free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4a90db69-a8cd-429d-b459-38d4e3c81613	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/minimax-m2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5a6fe5f6-d0b2-4445-9180-b434765b6cf3	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/minimax-m2.7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fd464aa7-814c-4474-a00d-f2d1e3d1c39f	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/minimax-m3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2d963681-b823-4aa6-bea7-73567b5c9557	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/nemotron-3-ultra-free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ac26a94a-1a67-45ef-b167-43eb4da80a3b	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/north-mini-code-free	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3668a0db-600e-4e1b-8389-b72f57d34c0c	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/qwen3.5-plus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7f702998-91eb-4c1e-9ef0-49c9a6c62b53	e383c6da-a54b-4224-986e-deee71353d2f	opencode-zen/qwen3.6-plus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a6e8b10c-75d6-4e56-b8c9-577096ea1686	e383c6da-a54b-4224-986e-deee71353d2f	Poolside/poolside/laguna-m.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a6f64c02-1b97-4208-92bd-b0406ab1267b	e383c6da-a54b-4224-986e-deee71353d2f	Poolside/poolside/laguna-xs-2.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e06dedfa-9e03-45b6-a060-7dc14d151675	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/black-forest-labs/FLUX-1.1-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
005fef4a-3fad-4655-b12b-aa06bfffcbc1	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/black-forest-labs/FLUX-1.1-pro-Ultra	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
72b147fb-f23a-4f4a-92d7-c8e9afbf7b25	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/black-forest-labs/FLUX.1-dev	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c0491233-5bb2-482a-93eb-a1a433cee1f9	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/black-forest-labs/FLUX.1-Kontext-dev	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
50574587-4475-4b95-bb43-7e00918975ad	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/black-forest-labs/FLUX.1-Kontext-max	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1a25a19e-4830-4ce3-9f43-b43433b8e74b	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/black-forest-labs/FLUX.1-Kontext-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f6de529c-cd63-4287-8ec3-b60db5b1dda2	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/black-forest-labs/FLUX.1-schnell	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
63bf515b-443e-4cba-b2c6-5183f2308e35	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/black-forest-labs/FLUX.2-flex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e5dee42f-fe3f-4eea-b06f-b9f4aacf30dc	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/black-forest-labs/FLUX.2-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0ae4b367-cc23-4e98-b19c-5febbd049a88	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/ByteDance-Seed/Seed-OSS-36B-Instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9ddbd12c-f4bc-4193-9588-8336ada90e89	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/deepseek-ai/DeepSeek-R1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8b626ddd-5069-470b-ad70-f0275f3ad648	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/deepseek-ai/DeepSeek-V3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0de37362-6f1c-4148-b0ed-5625b7844c1b	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/deepseek-ai/DeepSeek-V3.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7881bbb3-6d41-4fee-9d40-308a53b2d1bd	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/deepseek-ai/DeepSeek-V3.1-Terminus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6d39f795-08e3-43a8-a810-ba15f379fd98	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/deepseek-ai/DeepSeek-V3.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
851a0835-97f2-4def-8a54-f9144ae0c7ad	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/deepseek-ai/DeepSeek-V3.2-Exp	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d1d311e7-7629-4203-bfa6-d7d15a5bd014	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/deepseek-ai/DeepSeek-V4-Flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f4e23e77-56d7-4ff1-aaa9-cd4f6e28e894	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/deepseek-ai/DeepSeek-V4-Pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
da931cec-2568-4720-b9de-27b324626a51	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/fishaudio/fish-speech-1.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
83f23d3d-b849-482a-8e81-452e000085aa	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/FunAudioLLM/CosyVoice2-0.5B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
734e9fbf-9ba8-4696-ad80-cd4686ac7129	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/google/gemma-4-12B-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7f4e9446-b110-41ec-829b-910d78d246f6	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/google/gemma-4-26B-A4B-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2c20b043-2017-4b9f-a3d7-520089741123	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/google/gemma-4-31B-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d2f408c9-8449-42fe-b41e-1e7261eef711	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/inclusionAI/Ling-flash-2.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d99a7df5-f393-4b3e-a37f-ced868528269	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/IndexTeam/IndexTTS-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8b18e312-d425-4a59-9779-d6d6f45d2079	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/meituan-longcat/LongCat-2.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7d1a7e0b-5823-45a1-84d8-0825ed44e784	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/MiniMaxAI/MiniMax-M2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
27b07aae-7eb2-47ec-89a0-44cf2f947cf4	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/MiniMaxAI/MiniMax-M3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
dd743fe3-df88-428d-8d0d-a2b4bd5bc646	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/moonshotai/Kimi-K2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c35ce2be-bfb6-4691-8975-250f87740a33	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/moonshotai/Kimi-K2.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
405b7c9a-6b59-4711-811a-5b2afe4b8ace	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/moonshotai/Kimi-K2.7-Code	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3f4299bf-1b69-4b2a-be6c-502e411dcc2e	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/nex-agi/Nex-N2-Pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3d4acbb7-6f03-44f1-8e6c-9eea47199e2e	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/openai/gpt-oss-120b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c7a00ed1-08c6-4ae8-9ba1-77f6ab56eebe	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/openai/gpt-oss-20b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2baf1139-0327-480e-a908-d732c9457ff0	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen-Image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
be9c59d4-ce5f-47cf-8096-149ce748fb6c	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen-Image-Edit	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
52257af8-a547-4e7c-b2f2-1b8f1b49b8a9	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen2.5-72B-Instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a6a767ae-5f41-4ccc-8c92-7e600ec7bcee	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen2.5-7B-Instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c8ae3bce-114c-44dc-a5fd-81e739d56a52	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-14B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
69342419-b605-422e-88e1-80e7bc86accd	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-30B-A3B-Instruct-2507	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7c3ebd2b-df71-4e7b-af9e-9214b83cf5b3	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-32B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a11424b8-6b31-4689-896f-04a82bd59f24	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-8B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
38d27e1d-ea53-4a0c-984d-3c5cd9470d16	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-Coder-30B-A3B-Instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d9ebc8ad-e674-4b9b-a6b8-8ab48476cc4f	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-Embedding-0.6B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
022c3bad-c3d5-4168-ac3d-d8901d68d2f4	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-Embedding-4B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
125887a2-0215-4c14-8026-81fdc6d000fa	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-Embedding-8B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7258d637-4f38-471f-98a7-651c75d8b1c4	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-Reranker-0.6B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
39093c23-6905-4530-9964-63d844acff56	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-Reranker-8B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
efc90724-a4f0-4d82-87da-25e669f0e963	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-VL-30B-A3B-Instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
dd742841-5689-4702-800f-08315ec5f7ab	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-VL-30B-A3B-Thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7e76bdf8-9b50-431c-82db-822ea8135faa	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-VL-32B-Instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
533f005c-4cfc-49fb-b37b-89ca6c916fd6	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-VL-32B-Thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4e9a1481-9ce2-4aac-967b-3aee2ad850e5	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3-VL-8B-Instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
be7a9e9c-beea-4536-97d2-d78879711575	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3.5-122B-A10B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e3a70faa-7b63-476a-ae0c-faa647e19dd4	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3.5-27B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8ab8375a-a8b6-4ba6-8493-90cc41daf7d6	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3.5-35B-A3B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
390b0d28-2f64-4739-84bc-2de2df47cb91	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3.5-397B-A17B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
58581af1-2645-4f56-8a73-01bd5d938abf	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3.5-9B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
96ce57e2-d2f1-4571-afb7-e27060fdb646	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3.6-27B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0c1efe7f-259f-450a-a1bc-a0f135b563cf	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Qwen/Qwen3.6-35B-A3B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
81b87246-dd7b-42d6-a7a7-5846ea2db4a8	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/stepfun-ai/Step-3.5-Flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c4b645ee-10dc-47c5-b5ef-e76d46530f5b	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/tencent/Hunyuan-A13B-Instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
41b2e195-c969-46fd-9bb2-b5bf76dc9b42	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/tencent/Hy3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ce47312f-49bf-4d22-852b-cd789376e913	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/tencent/Hy3-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
477d86b2-46fd-4c56-abe4-eb85d9ab9eb4	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Tongyi-MAI/Z-Image-Turbo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8c86f8bb-5f1d-48ec-a8b8-c3cba0900e98	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Wan-AI/Wan2.2-I2V-A14B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4b494f95-a582-4b0f-a65f-307050103583	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/Wan-AI/Wan2.2-T2V-A14B	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8b371acf-b7a3-4222-b4ac-fb916c36b259	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/zai-org/GLM-4.5-Air	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9dd21c7b-d7b1-4230-b733-cebdbe1760e6	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/zai-org/GLM-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1a7d320d-305d-4b3f-b820-fe037857f378	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/zai-org/GLM-5.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7fbfc2c3-fcfb-4029-afcd-ec9b75fc4a1d	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/zai-org/GLM-5.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
42d1e8c1-d8b8-4a4b-ab12-b85a98a51083	e383c6da-a54b-4224-986e-deee71353d2f	siliconflow/zai-org/GLM-5V-Turbo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c15b5d86-d924-4604-8a4e-bddc2f6d40b8	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen-3-14b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
713c7475-dafa-45ad-b4f4-4e074b1a43a4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen-3-235b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c3681038-b55d-40b3-b3c7-388b7f8828ec	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen-3-30b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
19f5bd17-33d4-4ed3-b054-ef40e42a1616	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen-3-32b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f62ddf06-73ec-455f-8b16-bf018cb03a4f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen-3.6-max-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4d3f77a8-cbd0-40e1-91a9-e21c6460e4f0	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-235b-a22b-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9db27872-15b9-45cc-b3a0-ca3ef70b2e72	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-coder	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9b052da3-337f-4cbb-9136-e9cfa05ca5eb	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-coder-30b-a3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d10e6388-0225-46c9-96c4-ed513a7f8575	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-coder-next	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c8249c6f-033e-4ea5-99e7-018c9ff7ce64	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-coder-plus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a55e9135-9979-4770-8ef2-89c79f0cf104	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-embedding-0.6b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f04ee5e2-d8cb-4662-93f8-17e50194d037	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-embedding-4b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
efdecea8-e0f4-46a2-9209-d26840cf292e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-embedding-8b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ded2f34d-0c62-426e-bda7-058a351ee7b3	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-max	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9d3d9683-3469-4da1-b37f-0a6fd8532c87	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-max-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d3acbe58-81cd-4052-99fb-6ac6fea46727	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-max-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f60ff92f-077e-4b7c-bab6-6d49982eaad1	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-next-80b-a3b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b492c838-7a35-4ad7-bb6c-a54ccaea2128	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-next-80b-a3b-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
da2174e1-dbf9-4428-b787-319b08fb0a28	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-vl-235b-a22b-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
89c51c19-94c2-4fa7-b656-314585563edc	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-vl-instruct	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2a30c920-5a22-4086-9ff6-3121f3e8a6ff	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3-vl-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
10c74679-1391-4895-b645-da9eecd3d1e2	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c0b26cad-bda4-447f-a478-337ad443a9de	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3.5-plus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6ba8e568-213a-4e85-b1cd-efe8fef0ae6d	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3.6-27b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d6f0ca3a-daa4-4a14-afae-9756f2ae950a	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3.6-plus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
77fa4435-e957-4059-a033-e313be72a7f2	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3.7-max	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
931c563a-fb57-4f4d-b2e7-8cc303ce87c9	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/qwen3.7-plus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e6cf83ad-b902-49dd-b4f7-a527b10ecfcf	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/wan-v2.5-t2v-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8f9ed08c-61e5-4e47-9795-7db6c0a13033	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/wan-v2.6-i2v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
466eaf44-d2f4-4b1d-a172-135f1c2d77d4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/wan-v2.6-i2v-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
90cc6d0d-0d99-4002-8c50-1121624bb0a3	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/wan-v2.6-r2v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4f68c4a5-c6cc-4142-90ed-5310980df65e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/wan-v2.6-r2v-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b6a79eca-efb3-4cdf-9f6d-067939c2fe13	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/wan-v2.6-t2v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
302f9bba-65e8-4613-8cb5-0dfffa2d39eb	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/wan-v2.7-r2v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f6cae2f2-ae35-4788-a677-e7af959ac187	e383c6da-a54b-4224-986e-deee71353d2f	vercel/alibaba/wan-v2.7-t2v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
55989e62-43a7-42df-9cdd-4866b5223d29	e383c6da-a54b-4224-986e-deee71353d2f	vercel/amazon/nova-2-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
35bb842f-a729-48d8-a1ad-11b579cefcf4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/amazon/nova-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
db9b7dac-88e2-492c-880e-dcdac6e204e0	e383c6da-a54b-4224-986e-deee71353d2f	vercel/amazon/nova-micro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d8194645-c4f3-43b9-8bbb-2ca3d0e3435a	e383c6da-a54b-4224-986e-deee71353d2f	vercel/amazon/nova-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
65f77cb7-df9e-49f6-9128-1b31da88ecb3	e383c6da-a54b-4224-986e-deee71353d2f	vercel/amazon/titan-embed-text-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
119c7d58-06b8-491a-9280-bdbea81d6795	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-3-haiku	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cc632ae9-7bc6-4087-a715-080802522456	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-fable-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4b2650d5-606a-47e8-bc42-e2d78a149ec7	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-haiku-4.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
78b9c577-236f-4092-9688-c4d9fee04284	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-opus-4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
abd54505-adec-41cf-be76-eb9b75b295d3	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-opus-4.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
25a8fc89-5ca3-4afb-99fc-aec9440cee5c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-opus-4.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c05232b0-9efb-4758-b042-98bb3a3c4d80	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-opus-4.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8242d35f-19f6-4c72-9d9c-0a9251c7e1a9	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-opus-4.7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5da3175b-83c2-49b4-90e0-4f48db982bb0	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-opus-4.8	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e6ddcf82-dc1a-44ee-8dd6-5ae702f207d8	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-sonnet-4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
720d2069-00a7-4375-aee1-a5950d8bc21f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-sonnet-4.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f0ca1bc1-337c-48ef-b389-43108e627d06	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-sonnet-4.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d3783e20-a269-4b6c-816d-8bfd2cf359be	e383c6da-a54b-4224-986e-deee71353d2f	vercel/anthropic/claude-sonnet-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1142a303-7f88-46f6-a032-3f4ff818c4cf	e383c6da-a54b-4224-986e-deee71353d2f	vercel/arcee-ai/trinity-large-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3b1bbc11-63bb-4359-a489-255a1568d189	e383c6da-a54b-4224-986e-deee71353d2f	vercel/arcee-ai/trinity-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9ef83b42-8314-4ce4-96e1-261e18ce87d2	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bfl/flux-2-flex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0da503b7-54d7-493d-b418-ede710eff065	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bfl/flux-2-klein-4b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
21266a66-aae5-4050-8287-ac460d00ea93	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bfl/flux-2-klein-9b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8621bd0e-96f2-4f97-ac0c-4cca5d9bbc3b	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bfl/flux-2-max	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fd1bc095-8fc0-4288-8f65-3dee924422ad	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bfl/flux-2-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d5c0f87e-ca45-44b8-b1a4-af472c82b475	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bfl/flux-kontext-max	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5e32373c-625f-4c7a-a189-531f2629a3af	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bfl/flux-kontext-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ffe8bf6a-a293-4379-bcd1-706057440d96	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bfl/flux-pro-1.0-fill	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
14eab86d-2149-4a8c-aa88-8aa3b76ff513	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bfl/flux-pro-1.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fd2a7be5-592e-4fd2-83fd-2e72df85ac77	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bfl/flux-pro-1.1-ultra	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
08384ef3-1662-4fea-b8d8-428282f197a9	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bytedance/seed-1.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e0329ec9-c6e3-4808-8c9e-d300e93be9f8	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bytedance/seed-1.8	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
92d35b41-0607-49bf-a1fd-746022f7f0ad	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bytedance/seedance-2.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b7423e7d-1492-41b9-9574-251d14a06e80	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bytedance/seedance-2.0-fast	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e7f98bbd-a0db-4195-b1a1-a537554943af	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bytedance/seedance-v1.0-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e881a9b8-b443-4374-9f6d-29863f00b8bc	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bytedance/seedance-v1.0-pro-fast	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0ba8f3c1-e5be-4219-b103-76a6a7c264f6	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bytedance/seedance-v1.5-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
73935d22-605b-4994-b053-a8267c975802	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bytedance/seedream-4.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bfb90776-a084-4cbc-a927-7a25faed20dd	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bytedance/seedream-4.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3a6d5fce-3583-4a4a-9149-af24755a67c0	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bytedance/seedream-5.0-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7db91848-d72c-44f5-ba87-afd470854c2a	e383c6da-a54b-4224-986e-deee71353d2f	vercel/bytedance/seedream-5.0-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
89b3b890-0324-4800-947e-0c183cd4e6f7	e383c6da-a54b-4224-986e-deee71353d2f	vercel/cohere/command-a	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e19ad281-6e70-45e9-a80c-d882373d341f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/cohere/embed-v4.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
976fb407-6e77-49d1-864c-5788e886603e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/cohere/rerank-v3.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
455079a2-d843-4484-bc19-a4c0943a2526	e383c6da-a54b-4224-986e-deee71353d2f	vercel/cohere/rerank-v4-fast	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f56cf55a-7705-4731-8682-02a37e352466	e383c6da-a54b-4224-986e-deee71353d2f	vercel/cohere/rerank-v4-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
037d709c-52e6-4a1e-8579-fcd926925c1e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/deepseek/deepseek-r1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ad0369ec-47f3-464c-8533-762c092f5e30	e383c6da-a54b-4224-986e-deee71353d2f	vercel/deepseek/deepseek-v3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e5bd33d7-f50f-458a-a478-9b7ed773bde5	e383c6da-a54b-4224-986e-deee71353d2f	vercel/deepseek/deepseek-v3.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
efd10f96-9e8b-4222-a708-78c1ec408881	e383c6da-a54b-4224-986e-deee71353d2f	vercel/deepseek/deepseek-v3.1-terminus	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ccd4158b-9ef7-4626-b4fc-cc6069187d3c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/deepseek/deepseek-v3.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0f8745a9-9ff1-4134-be2c-542ba641623b	e383c6da-a54b-4224-986e-deee71353d2f	vercel/deepseek/deepseek-v3.2-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
99a6aec8-a319-48f2-ac06-65e10fc3a10a	e383c6da-a54b-4224-986e-deee71353d2f	vercel/deepseek/deepseek-v4-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
326ba08a-27b6-4b09-ba03-fccda9cb88ee	e383c6da-a54b-4224-986e-deee71353d2f	vercel/deepseek/deepseek-v4-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9b14a857-961c-4bd3-83c1-8366637b1df8	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-2.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
753fa8bf-a77e-46e3-b690-cbe80d3aa611	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-2.5-flash-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6505b7ec-a93d-431a-a0f9-9fc46c90bfe7	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-2.5-flash-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d2c14194-c13a-4974-9c3e-0489abb1b89a	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-2.5-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f154aaeb-cd25-454f-94cd-85ff45dee288	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-3-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
af1b16b8-f8b6-4f4d-8960-cf509cb653d6	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-3-pro-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c78ec030-b00e-477a-8644-154dcb209f34	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-3-pro-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2e8118a1-1d50-4ae4-a100-15d9757c14fa	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-3.1-flash-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6b9376d8-19c6-44ee-a571-895189df8103	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-3.1-flash-image-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
28fce6f8-b297-4057-843a-ed68c3efbf9e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-3.1-flash-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1deb404b-75b0-4bae-a973-dcc35f50dc61	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-3.1-flash-lite-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
319c874e-0614-4c0d-bbd8-f80a428afced	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-3.1-flash-lite-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5ab9c3f6-34dd-4656-8f38-50b3943c8c03	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-3.1-pro-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e2bc6e37-349a-4452-89ac-553d1fcf9e1c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-3.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
079d9e67-7719-4e37-af3b-2ea0b5dd0452	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-embedding-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ba6567dc-b0fe-4991-8ae6-564900e3e1f4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-embedding-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b2f3a633-5d1e-4924-a7ec-a8533d2c0a76	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemini-omni-flash-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
41c908ac-a05c-4c95-b505-d3f825e5fe21	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemma-4-26b-a4b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
814bfddf-3036-48f5-b1ee-fb42404c6f48	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/gemma-4-31b-it	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
149409f3-3501-4ffc-a23d-240dfabd8d1b	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/imagen-4.0-fast-generate-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
80c0e296-8249-4926-a193-50bf5ce2aac8	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/imagen-4.0-generate-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
722302de-a55d-42c1-83d5-8c0e781c8d80	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/imagen-4.0-ultra-generate-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f1375bd4-9722-4079-ae03-d4997b759cc5	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/text-embedding-005	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
af5beb77-ff3a-4669-982e-989a1ce28ece	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/text-multilingual-embedding-002	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
959e74a8-f54e-4654-a4fe-0d0eaf09907b	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/veo-3.0-fast-generate-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5779df4e-a3b2-49fe-9132-efbaf2f96233	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/veo-3.0-generate-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5a072ecd-c93e-40e6-a142-1ef1d8ff9dab	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/veo-3.1-fast-generate-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
98883c42-63f5-4d8b-809a-5b54a20484c6	e383c6da-a54b-4224-986e-deee71353d2f	vercel/google/veo-3.1-generate-001	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c835c7ad-ac57-4661-8afe-cfea293822d5	e383c6da-a54b-4224-986e-deee71353d2f	vercel/inception/mercury-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
26b546e2-fa11-4715-9c01-5c20e7cbb5d4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/inception/mercury-coder-small	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
eeebf09c-ce91-40ad-96e9-fc38b6a216d5	e383c6da-a54b-4224-986e-deee71353d2f	vercel/interfaze/interfaze-beta	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
99176c93-700e-4dc9-a55a-b13c3daa76c5	e383c6da-a54b-4224-986e-deee71353d2f	vercel/klingai/kling-v2.5-turbo-i2v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
69ab1bc9-ec2a-4076-a472-4b846a23b5a8	e383c6da-a54b-4224-986e-deee71353d2f	vercel/klingai/kling-v2.5-turbo-t2v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
89b9e8fc-5c4c-4d03-bc42-8763d6c25b7e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/klingai/kling-v2.6-i2v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
75999e9e-e046-4305-8c09-7f8359338735	e383c6da-a54b-4224-986e-deee71353d2f	vercel/klingai/kling-v2.6-motion-control	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5266e80e-9fdb-4c01-bfb7-e19234a45b24	e383c6da-a54b-4224-986e-deee71353d2f	vercel/klingai/kling-v2.6-t2v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d2010a6b-2e8f-4df6-bdd3-bda40a056968	e383c6da-a54b-4224-986e-deee71353d2f	vercel/klingai/kling-v3.0-i2v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f2f7206b-17b4-4b6f-a811-8aba41afe800	e383c6da-a54b-4224-986e-deee71353d2f	vercel/klingai/kling-v3.0-motion-control	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
df0849d2-f3ff-4d65-af51-11dd36af87c6	e383c6da-a54b-4224-986e-deee71353d2f	vercel/klingai/kling-v3.0-t2v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e6a8ab77-1c17-438f-9555-a64fc49e1fda	e383c6da-a54b-4224-986e-deee71353d2f	vercel/kwaipilot/kat-coder-air-v2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c9461b28-7bad-431c-bd58-99295cfb01dd	e383c6da-a54b-4224-986e-deee71353d2f	vercel/kwaipilot/kat-coder-pro-v1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d7c67ffd-b0b5-4504-81d7-06a80039d5c7	e383c6da-a54b-4224-986e-deee71353d2f	vercel/kwaipilot/kat-coder-pro-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a553efdb-0125-4cce-9fbb-5e5fae18c216	e383c6da-a54b-4224-986e-deee71353d2f	vercel/kwaipilot/kat-coder-pro-v2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ea5e4832-bd2e-47a6-9b8b-ce7543e61102	e383c6da-a54b-4224-986e-deee71353d2f	vercel/meta/llama-3.1-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f9e7d61a-5d4a-4b00-b1e4-45d4e9f37d8c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/meta/llama-3.1-8b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
341de0ec-92d0-4e07-bb7a-c79632f0a375	e383c6da-a54b-4224-986e-deee71353d2f	vercel/meta/llama-3.2-11b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b851b4c6-5408-4ee0-a59f-aadaa031ab59	e383c6da-a54b-4224-986e-deee71353d2f	vercel/meta/llama-3.2-1b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8cbf880d-6fd7-4f9a-8924-615ddaf56a13	e383c6da-a54b-4224-986e-deee71353d2f	vercel/meta/llama-3.2-3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
64f2dbdb-f5f6-4120-bfb3-c6a49155f8d9	e383c6da-a54b-4224-986e-deee71353d2f	vercel/meta/llama-3.2-90b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4526d969-d117-43ff-ae48-e178e21e7ced	e383c6da-a54b-4224-986e-deee71353d2f	vercel/meta/llama-3.3-70b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3b37cbb3-245e-4fdb-a0de-3687588f71ec	e383c6da-a54b-4224-986e-deee71353d2f	vercel/meta/llama-4-maverick	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5ab49851-9aa5-4c31-b56f-6efa067e8183	e383c6da-a54b-4224-986e-deee71353d2f	vercel/meta/llama-4-scout	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6d22e0c0-2c06-4521-86e0-3d4a03aee1d4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/meta/muse-spark-1.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
00ec9872-c953-4344-9368-eba80fb8e733	e383c6da-a54b-4224-986e-deee71353d2f	vercel/minimax/minimax-m2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
897b758e-d2ea-4ad7-ab2c-614ac4aa6529	e383c6da-a54b-4224-986e-deee71353d2f	vercel/minimax/minimax-m2.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
97378132-dbf8-471e-8a12-ac8e2a211209	e383c6da-a54b-4224-986e-deee71353d2f	vercel/minimax/minimax-m2.1-lightning	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2efeb18e-7806-4ed9-82ad-bd8ff0f43e8b	e383c6da-a54b-4224-986e-deee71353d2f	vercel/minimax/minimax-m2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fc6e416e-5392-44a7-9918-5165e1c33d8c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/minimax/minimax-m2.5-highspeed	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bd320ca1-017d-4448-81f0-754337b7343e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/minimax/minimax-m2.7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f8a3d0cd-8bf4-4e45-8b42-326e6401be5e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/minimax/minimax-m2.7-highspeed	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9735459e-b714-46a7-a040-597c1852e2d6	e383c6da-a54b-4224-986e-deee71353d2f	vercel/minimax/minimax-m3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ba7ef73e-938f-4372-85f0-0c1f09578e0a	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/codestral	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bfb28f15-74d3-4ec2-85af-5602e25cc3b2	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/codestral-embed	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7dcc1ee2-46c4-445a-b89a-40991cd5485d	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/devstral-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c340066e-c081-430e-a3e6-1a839ec3db94	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/devstral-small-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5754cfa5-8fad-4f67-8d2f-91296c33da9d	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/magistral-medium	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
33531df8-80d3-4bb0-ad79-0ee262e5ecf2	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/magistral-small	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2f5297cf-dcf3-4dfc-93a9-b1be102d15cd	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/ministral-14b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
855f3b2a-71d6-4182-ac86-16d348d56932	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/ministral-3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1122f2a8-2831-47fd-80fe-b74e909fbe45	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/ministral-8b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
37f0f6e3-7942-4615-b380-fb8b8aad90f4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/mistral-embed	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
43f03b7c-d725-4dc7-89c1-63cb12fa376a	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/mistral-large-3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
76e18533-7835-45d1-902d-d6fec831c1c1	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/mistral-medium	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
727dc6ab-c7da-4e7a-8d82-0354d903b994	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/mistral-medium-3.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9f47239b-8819-4fce-b334-ae8d2df3e6cd	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/mistral-nemo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
347ea624-6bf9-4e0c-8b1f-e1de1a88d3e1	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/mistral-small	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b82c4654-9db2-44c0-915c-b3aafcb3c6ef	e383c6da-a54b-4224-986e-deee71353d2f	vercel/mistral/pixtral-12b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
91217060-bf95-4912-a45e-2551f9a9a492	e383c6da-a54b-4224-986e-deee71353d2f	vercel/moonshotai/kimi-k2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
87f6ec45-36f6-4bd8-ad61-6abaf0570acc	e383c6da-a54b-4224-986e-deee71353d2f	vercel/moonshotai/kimi-k2-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7f0eba7c-e7ae-46e0-8890-7c248ab7a7db	e383c6da-a54b-4224-986e-deee71353d2f	vercel/moonshotai/kimi-k2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
eed1289f-7a9e-46de-8c83-82bcfc3cb762	e383c6da-a54b-4224-986e-deee71353d2f	vercel/moonshotai/kimi-k2.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
29d575ab-28af-4c47-bbd9-c2c58d261251	e383c6da-a54b-4224-986e-deee71353d2f	vercel/moonshotai/kimi-k2.7-code	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5202921b-57da-4696-a1f2-c8d4064878b9	e383c6da-a54b-4224-986e-deee71353d2f	vercel/moonshotai/kimi-k2.7-code-highspeed	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
87763202-8e99-496a-b203-9df53405100c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/morph/morph-v3-fast	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c95c7107-92f0-4c9e-8035-b13ce9de241f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/morph/morph-v3-large	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cb780474-c0f2-4f5d-9a06-5544579eb28b	e383c6da-a54b-4224-986e-deee71353d2f	vercel/nvidia/nemotron-3-nano-30b-a3b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0a662614-70cd-4744-b4e3-8093e9456cbe	e383c6da-a54b-4224-986e-deee71353d2f	vercel/nvidia/nemotron-3-super-120b-a12b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
664f1882-d0b7-4358-a18a-12e636b416d0	e383c6da-a54b-4224-986e-deee71353d2f	vercel/nvidia/nemotron-3-ultra-550b-a55b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ea603a7b-0b2e-4747-a618-4d1df76faa4e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/nvidia/nemotron-nano-12b-v2-vl	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
682a01ef-9c03-498f-9e31-fef9a71d5c87	e383c6da-a54b-4224-986e-deee71353d2f	vercel/nvidia/nemotron-nano-9b-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
922fd6d7-1878-4527-b5ac-07cb15974fc0	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-3.5-turbo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a373d791-aab5-42b1-b2ee-0b14ab05d95e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-4-turbo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
885e9456-a344-46a1-be48-8bd4ad57bf8e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-4.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
51415a68-f382-41c7-8b8a-59929393ab0e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-4.1-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
77de5f3d-8300-4bd4-a61f-a3c8c613669f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-4.1-nano	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6f2632dd-43c2-481e-90e4-158fc9c89899	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-4o	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6da0f3eb-5a35-48f1-8348-5b210b309bc7	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-4o-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a1fb4175-fa62-4a5a-a551-fc24bb672b16	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-4o-mini-search-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7f0008a1-6727-4683-8ce0-51a5d27e1beb	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-4o-mini-transcribe	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e2a03561-2d18-4526-af87-af2c0defab84	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-4o-transcribe	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
dc1de40c-69b3-4a60-9160-9f6f5763dcfa	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
40fa1c73-ce94-480c-86ae-dfb087602058	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5-chat	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b74b7758-b8b8-4bae-bea5-62725718390d	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5-codex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
72a1df0b-3ccc-4f70-b895-4a7fa2899087	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
530383af-f75c-421a-a12b-f92f112d1754	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5-nano	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
73ae1220-e298-4872-92c3-dfa9cd703922	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
74fe76e8-4051-4c01-822d-ebfb25c86fd0	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.1-codex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
67771fab-41c0-4fc4-ac45-0f933a5ebf26	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.1-codex-max	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f789918b-905e-413d-996e-9b50f9a70021	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.1-codex-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
546cd746-05b1-4b1e-8b23-0e342c1fcb22	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.1-instant	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b7d0d37f-7a11-4e46-8e2b-43b8af72444a	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.1-thinking	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
619b7a00-6a5a-4387-a917-12986e7acdf4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7b027723-13c9-4e62-8bd1-a1f748be1628	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.2-chat	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
509f1240-62d4-4890-952a-1478927089ed	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.2-codex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2a0be9fb-b8cf-478d-9ca4-15723ca9e095	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.2-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
22cc87af-2df8-49bb-a446-38e6a870426f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.3-chat	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
22e8087a-5ae5-4b8a-9962-739c59fc8db4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.3-codex	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
93844d37-8ff6-4433-adad-ba3222006fd4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
03abac38-0843-4d69-80f3-2f54138feb01	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.4-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6828e46e-fafb-409b-9bdb-aff9c3c051b2	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.4-nano	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c1bb3ec7-bd36-42b8-bfea-ef8b546ed465	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.4-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
dc7a125a-aff2-4ce1-86e2-8cc4ca7d65ee	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
115b1369-ea69-43b5-863b-41614aed5ad5	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.5-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
418a27d7-6c4a-42b0-88de-4e9376e0f7d3	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.6-luna	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c9d10b5b-86bd-4ac1-9f3a-5ddf93a80efb	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.6-sol	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f6415222-20d4-4d0f-812c-ff5b1d2d0d51	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-5.6-terra	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8658956d-3225-4d91-aea0-c558ab9bc754	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-image-1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5a21dab6-0fe6-40ea-b8de-cb8ad4034958	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-image-1-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
939a27b1-f05c-4f01-ab68-181a353fa223	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-image-1.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
bbf53007-9845-454a-8601-3f83e6414723	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-image-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
48ed201c-e139-47da-89ba-2e690bef5201	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-oss-120b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e2603a1f-bc1a-4b07-bcc0-b26a35c05c46	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-oss-20b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cf317eb0-ca64-48a7-866c-0630bc54329b	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-oss-safeguard-20b	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3c98b7cc-6dce-46e3-8688-d5ab15dc5c98	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-realtime-1.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9c809edb-7d4e-4cf6-a093-994880a5def7	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-realtime-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5dc405aa-1276-4b34-b8b9-ed8dffd76cf4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-realtime-2.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
94af05c7-2840-4772-acf0-948163bcfe8a	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/gpt-realtime-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f06ac053-d059-422b-b5f8-25e0894a3793	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/o1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
11b710fb-cd10-42c6-b963-458fe37e3dcf	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/o3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1b67323a-51d8-453f-9219-e338f152fa01	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/o3-deep-research	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9e22ceb0-7b58-45a4-9d51-79a157d470b0	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/o3-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
cf0485c4-160e-4493-a036-de82b3a66325	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/o3-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
30c7bff8-b722-47f2-be2d-804f025c463b	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/o4-mini	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
fe29397e-9919-4746-8c2f-a4a6049d490f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/text-embedding-3-large	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
891e8078-49d4-429d-9b22-db3cf81ab8bd	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/text-embedding-3-small	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
15f83fb4-01fc-44b2-8451-d96bb2fc64b4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/text-embedding-ada-002	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8111080e-e802-434b-909c-3a11e3ab5dcc	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/tts-1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
08b583c3-8853-4a40-bb30-57ccbeac17f9	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/tts-1-hd	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ff5aa5e2-38d4-43e1-a6a2-5aa1cdb3348d	e383c6da-a54b-4224-986e-deee71353d2f	vercel/openai/whisper-1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ab024228-693e-4699-8de1-818ae93d523f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/perplexity/sonar	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5bb01395-b678-4cd2-abbd-469e15d47804	e383c6da-a54b-4224-986e-deee71353d2f	vercel/perplexity/sonar-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
da06b076-9d51-46f4-bfbf-7cf4ce0feff0	e383c6da-a54b-4224-986e-deee71353d2f	vercel/perplexity/sonar-reasoning-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4cefae04-14b4-47dc-86e7-1300e5522e82	e383c6da-a54b-4224-986e-deee71353d2f	vercel/prodia/flux-fast-schnell	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5b02d1ec-3d50-40fa-9f15-892e9ac7e335	e383c6da-a54b-4224-986e-deee71353d2f	vercel/quiverai/arrow-1.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
ad1865de-bb28-4154-999a-6a6131f5caa1	e383c6da-a54b-4224-986e-deee71353d2f	vercel/recraft/recraft-v2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1858abaf-8657-4578-836c-c7a47e910ca4	e383c6da-a54b-4224-986e-deee71353d2f	vercel/recraft/recraft-v3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b520950c-9735-45ee-b8e3-7705799f88ec	e383c6da-a54b-4224-986e-deee71353d2f	vercel/recraft/recraft-v4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
abf8b88d-8f49-43e3-8842-45ed07426e67	e383c6da-a54b-4224-986e-deee71353d2f	vercel/recraft/recraft-v4-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e6a170a1-bac3-4cbc-a5b2-5b0260d7f8e6	e383c6da-a54b-4224-986e-deee71353d2f	vercel/recraft/recraft-v4.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
15774eea-888c-454e-bbe1-34a3942d91a7	e383c6da-a54b-4224-986e-deee71353d2f	vercel/recraft/recraft-v4.1-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b22c197f-4025-4904-b811-69da3fd61f3f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/recraft/recraft-v4.1-utility	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
be3b1618-6526-45aa-8c5a-6c0ecc9f1fea	e383c6da-a54b-4224-986e-deee71353d2f	vercel/recraft/recraft-v4.1-utility-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1bf4adbd-efc7-41fb-8181-9b9451af33fd	e383c6da-a54b-4224-986e-deee71353d2f	vercel/sakana/fugu-ultra	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a1069284-0d96-456b-907e-a75f25cf8ffa	e383c6da-a54b-4224-986e-deee71353d2f	vercel/stepfun/step-3.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6e285916-48d6-4924-bc40-e06b43c555fb	e383c6da-a54b-4224-986e-deee71353d2f	vercel/stepfun/step-3.7-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e203161b-681f-4e5d-a1dd-e76c44976bce	e383c6da-a54b-4224-986e-deee71353d2f	vercel/voyage/rerank-2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
9abf2a93-a051-4ac7-a5b0-ba5f495f9b3c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/voyage/rerank-2.5-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f8f82c96-2f63-483f-9357-b897a4aab8aa	e383c6da-a54b-4224-986e-deee71353d2f	vercel/voyage/voyage-3-large	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f979a83a-a2e1-4970-a0f5-39ce811707ca	e383c6da-a54b-4224-986e-deee71353d2f	vercel/voyage/voyage-3.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5cbb3d1b-51b2-46d2-8358-65531a94346c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/voyage/voyage-3.5-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8b1b254c-1da8-46f2-ba69-41f47c620a23	e383c6da-a54b-4224-986e-deee71353d2f	vercel/voyage/voyage-4	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
031e65ea-1e3b-482c-b9c4-c3bad343b0de	e383c6da-a54b-4224-986e-deee71353d2f	vercel/voyage/voyage-4-large	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0e898f41-39d1-4c5d-a03b-51dcc77e363f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/voyage/voyage-4-lite	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
de9b5d30-76a6-49e3-8523-6e9bc3283b1f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/voyage/voyage-code-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8b23a2fa-4a3c-4caa-bbe9-00bfb7d17bcf	e383c6da-a54b-4224-986e-deee71353d2f	vercel/voyage/voyage-code-3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e1755f91-237b-4b1f-bca7-99b57c71550b	e383c6da-a54b-4224-986e-deee71353d2f	vercel/voyage/voyage-finance-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
37260b95-5c8e-4f88-8370-172cb6e69594	e383c6da-a54b-4224-986e-deee71353d2f	vercel/voyage/voyage-law-2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6faa0db1-9f36-49f1-b1ce-082f3356364c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-4.1-fast-non-reasoning	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
2b5f0f9c-c7f3-4608-ba88-b1da9da34d08	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-4.1-fast-reasoning	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
16a42ccf-bed9-4cd6-95b8-1355318b4caf	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-4.20-multi-agent	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
a353536c-4a0b-492f-8e40-98fed522a08c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-4.20-multi-agent-beta	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
08d66ec7-3ca6-4c6a-9d02-5275229ea880	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-4.20-non-reasoning	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
e2e7b4f2-a376-4856-bb47-24438ea5367e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-4.20-non-reasoning-beta	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
21308b0f-5492-479a-a99d-e9df5e4f1359	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-4.20-reasoning	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c0cae951-2970-4956-bfae-0b07ae8f5fbb	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-4.20-reasoning-beta	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
d67d675f-8571-468a-98fc-2ee98af1debe	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-4.3	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1568de15-d897-49c9-8c51-bfcb03905e9c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-4.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4c91f1e8-fe48-4983-8ef0-d58c5d4e130f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-build-0.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c8f5eee9-569d-4899-a6d2-8b16dc1850f0	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-imagine-image	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
817f36f8-c72e-410d-a1da-2cb92014d83c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-imagine-video	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
0cc53c37-fbe8-4e5b-95d3-bb0479625087	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-imagine-video-1.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3a272bfe-94fe-4c04-bc21-033efc7856ae	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-imagine-video-1.5-preview	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
927dfe90-3eaf-4550-a88c-ec2e8b1608c9	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-stt	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
1ee950a0-1342-4579-a080-755aedcddb5b	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-tts	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
92618942-9526-4d8f-839b-ffdbd44771e7	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xai/grok-voice-think-fast-1.0	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6dc7af61-1785-461d-89e2-979dfb4d167d	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xiaomi/mimo-v2.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
aadc15fd-344e-4399-b5e8-ee8c4e7459f9	e383c6da-a54b-4224-986e-deee71353d2f	vercel/xiaomi/mimo-v2.5-pro	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
3c72367a-9dbb-46f7-a0fe-f06e34327abd	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-4.5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
923a52f6-279c-41e1-8d4f-e7763373d81e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-4.5-air	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
44fb96f0-89ca-47db-9314-2e8df059eb41	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-4.5v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
277e6844-1087-4b5a-a807-0800a60e8a3c	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-4.6	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b451e88a-9d90-4016-b888-8305140470d2	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-4.6v	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f949c4d7-12c5-4c3b-a9f9-0d890213b178	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-4.6v-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8c03d663-99fd-43e6-bf3a-5906e42a0334	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-4.7	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
7f5eb04c-8b9d-4ae7-95d4-3e737372006e	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-4.7-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5d731153-16d0-4c95-b425-9c406d97a109	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-4.7-flashx	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
5dc3a4a4-0061-4682-873d-ab77abbf4bb2	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-5	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
8bbaf659-3a6e-4731-806b-70b0c548e55a	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-5-turbo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
4cdf8826-0c56-4ee8-b059-d8ed22cbeac6	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-5.1	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
925ba34f-b8a1-4384-873f-9c396ac7047f	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-5.2	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
83b24314-9f19-47a7-8ee4-3986e3114acf	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-5.2-fast	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
b84c6d2c-f4ab-4d35-9994-ad21cd277b14	e383c6da-a54b-4224-986e-deee71353d2f	vercel/zai/glm-5v-turbo	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
f717247d-5b6d-4ed5-bf30-66c2055e6fc0	e383c6da-a54b-4224-986e-deee71353d2f	z-ai/glm-4.5-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
c0625664-d723-4f4a-b456-d5563b627e7c	e383c6da-a54b-4224-986e-deee71353d2f	z-ai/glm-4.6v-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
6ea3ab88-5af3-44c4-88cd-8ff592411788	e383c6da-a54b-4224-986e-deee71353d2f	z-ai/glm-4.7-flash	f	t	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:42.327385+00	2026-07-16 08:50:26.96405+00	2026-07-16 08:50:26.96405+00
\.


--
-- Data for Name: model_endpoints; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.model_endpoints (id, name, base_url, encrypted_api_key, enabled, created_at, updated_at) FROM stdin;
e383c6da-a54b-4224-986e-deee71353d2f	bifrost	http://100.117.136.97:34521/v1	5l0KUD42HmvxrRvt4DhFZSOTwkV33k7ToeLtvuCfK2lsR2D-UharvFc_eK8xSQQvZkectZXGg4Y23ewlVUoRJE-M8gKe5w==	t	2026-07-16 08:24:41.631542+00	2026-07-16 08:26:13.281555+00
\.


--
-- Data for Name: model_fallback_entries; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.model_fallback_entries (id, model_id, "position", created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: model_preferences; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.model_preferences (id, primary_model_id, utility_model_id, image_model_id, created_at, updated_at) FROM stdin;
1	3f0569db-8895-44f2-84df-2ceecb0764d4	be4e714e-04e6-4b00-ace2-63c26bb28f5c	\N	2026-07-16 08:24:19.277551+00	2026-07-17 04:39:56.966931+00
\.


--
-- Data for Name: model_profiles; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.model_profiles (model_id, display_name, context_window, max_output_tokens, token_parameter, temperature, top_p, reasoning_effort, supports_chat, supports_streaming, created_at, updated_at) FROM stdin;
3f0569db-8895-44f2-84df-2ceecb0764d4	Ella Small	\N	\N	max_tokens	\N	\N	high	t	t	2026-07-17 00:43:23.741978+00	2026-07-17 00:43:23.741978+00
\.


--
-- Data for Name: model_sync_runs; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.model_sync_runs (id, endpoint_id, status, models_found, error_code, error_message, started_at, finished_at) FROM stdin;
82e16117-aa48-4eed-8583-033f84b6fad0	e383c6da-a54b-4224-986e-deee71353d2f	failed	0	invalid_response	The endpoint returned invalid JSON.	2026-07-16 08:24:54.572562+00	2026-07-16 08:24:54.647431+00
b409d2ac-e598-4906-a78e-9277d4f9ac31	e383c6da-a54b-4224-986e-deee71353d2f	failed	0	timeout	The endpoint did not respond before the timeout.	2026-07-16 08:25:35.533254+00	2026-07-16 08:25:45.575006+00
4ec21f63-6066-45d4-8bb7-6694bf8b20ef	e383c6da-a54b-4224-986e-deee71353d2f	failed	0	timeout	The endpoint did not respond before the timeout.	2026-07-16 08:26:30.015479+00	2026-07-16 08:26:40.032872+00
fbb103c7-e654-41e7-b632-d7a3a0497aaf	e383c6da-a54b-4224-986e-deee71353d2f	failed	0	timeout	The endpoint did not respond before the timeout.	2026-07-16 08:26:55.670619+00	2026-07-16 08:27:05.700057+00
bde595e2-e039-464f-9774-fe1c37b64be4	e383c6da-a54b-4224-986e-deee71353d2f	failed	0	timeout	The endpoint did not respond before the timeout.	2026-07-16 08:28:00.396185+00	2026-07-16 08:28:10.414024+00
bfb01779-4b23-4167-a9bb-b3500fe7c1f6	e383c6da-a54b-4224-986e-deee71353d2f	failed	0	timeout	The endpoint did not respond before the timeout.	2026-07-16 08:37:59.015129+00	2026-07-16 08:38:09.036564+00
ee910cbf-b56b-4c57-a31f-cd6b3d38b084	e383c6da-a54b-4224-986e-deee71353d2f	succeeded	1135	\N	\N	2026-07-16 08:50:26.967754+00	2026-07-16 08:50:42.327385+00
\.


--
-- Data for Name: persona_preferences; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.persona_preferences (id, default_persona_id, created_at, updated_at) FROM stdin;
1	00000000-0000-0000-0000-000000000011	2026-07-17 02:14:25.997612+00	2026-07-17 02:14:25.997612+00
\.


--
-- Data for Name: personas; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.personas (id, name, description, instructions, enabled, instruction_role, created_at, updated_at) FROM stdin;
00000000-0000-0000-0000-000000000011	Ella	Migrated from the original global persona.	Your name is Ella. And you is a charismatic personal assistant of Yuri.	t	system	2026-07-16 09:00:21.553462+00	2026-07-16 23:03:37.135031+00
72875fa4-fc71-422d-be29-b01887ec16bd	Ella copy	Migrated from the original global persona.	Your name is Ella. And you is a charismatic personal assistant of Yuri.	t	system	2026-07-17 02:16:28.967702+00	2026-07-17 02:16:28.967702+00
\.


--
-- Data for Name: retrieval_preferences; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.retrieval_preferences (id, embedding_model_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: retrieval_usages; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.retrieval_usages (id, assistant_message_id, kind, memory_id, chunk_id, rank, score, label, content_snapshot, created_at) FROM stdin;
\.


--
-- Data for Name: tool_executions; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.tool_executions (id, conversation_id, assistant_message_id, tool_message_id, tool_id, tool_call_id, tool_name, arguments, status, result, error_message, started_at, finished_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: aster
--

COPY public.users (id, username, password_hash, password_changed_at, created_at, updated_at) FROM stdin;
1	yuri	$argon2id$v=19$m=19456,t=2,p=1$GNoEthfK2wGXaY4jEVaqoA$0f1shZ1zrT057MMSzvTagoXjzCDcfvwozKwMw1d8ReM	2026-07-16 21:43:06.520767+00	2026-07-16 21:43:06.519931+00	2026-07-16 21:43:06.519931+00
\.


--
-- Name: model_preferences_id_seq; Type: SEQUENCE SET; Schema: public; Owner: aster
--

SELECT pg_catalog.setval('public.model_preferences_id_seq', 1, false);


--
-- Name: persona_preferences_id_seq; Type: SEQUENCE SET; Schema: public; Owner: aster
--

SELECT pg_catalog.setval('public.persona_preferences_id_seq', 1, false);


--
-- Name: retrieval_preferences_id_seq; Type: SEQUENCE SET; Schema: public; Owner: aster
--

SELECT pg_catalog.setval('public.retrieval_preferences_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: aster
--

SELECT pg_catalog.setval('public.users_id_seq', 1, false);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: auth_sessions auth_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_pkey PRIMARY KEY (id);


--
-- Name: auth_sessions auth_sessions_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_token_hash_key UNIQUE (token_hash);


--
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


--
-- Name: conversation_collections conversation_collections_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.conversation_collections
    ADD CONSTRAINT conversation_collections_pkey PRIMARY KEY (conversation_id, collection_id);


--
-- Name: conversation_retrieval_settings conversation_retrieval_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.conversation_retrieval_settings
    ADD CONSTRAINT conversation_retrieval_settings_pkey PRIMARY KEY (conversation_id);


--
-- Name: conversation_tools conversation_tools_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.conversation_tools
    ADD CONSTRAINT conversation_tools_pkey PRIMARY KEY (conversation_id, tool_id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: image_model_profiles image_model_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_model_profiles
    ADD CONSTRAINT image_model_profiles_pkey PRIMARY KEY (model_id);


--
-- Name: image_operation_inputs image_operation_inputs_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operation_inputs
    ADD CONSTRAINT image_operation_inputs_pkey PRIMARY KEY (operation_id, asset_id);


--
-- Name: image_operation_outputs image_operation_outputs_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operation_outputs
    ADD CONSTRAINT image_operation_outputs_pkey PRIMARY KEY (operation_id, asset_id);


--
-- Name: image_operations image_operations_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operations
    ADD CONSTRAINT image_operations_pkey PRIMARY KEY (id);


--
-- Name: knowledge_chunks knowledge_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.knowledge_chunks
    ADD CONSTRAINT knowledge_chunks_pkey PRIMARY KEY (id);


--
-- Name: knowledge_collections knowledge_collections_name_key; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.knowledge_collections
    ADD CONSTRAINT knowledge_collections_name_key UNIQUE (name);


--
-- Name: knowledge_collections knowledge_collections_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.knowledge_collections
    ADD CONSTRAINT knowledge_collections_pkey PRIMARY KEY (id);


--
-- Name: knowledge_documents knowledge_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.knowledge_documents
    ADD CONSTRAINT knowledge_documents_pkey PRIMARY KEY (id);


--
-- Name: mcp_servers mcp_servers_name_key; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.mcp_servers
    ADD CONSTRAINT mcp_servers_name_key UNIQUE (name);


--
-- Name: mcp_servers mcp_servers_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.mcp_servers
    ADD CONSTRAINT mcp_servers_pkey PRIMARY KEY (id);


--
-- Name: mcp_tools mcp_tools_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.mcp_tools
    ADD CONSTRAINT mcp_tools_pkey PRIMARY KEY (id);


--
-- Name: media_assets media_assets_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.media_assets
    ADD CONSTRAINT media_assets_pkey PRIMARY KEY (id);


--
-- Name: memories memories_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.memories
    ADD CONSTRAINT memories_pkey PRIMARY KEY (id);


--
-- Name: memory_suggestions memory_suggestions_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.memory_suggestions
    ADD CONSTRAINT memory_suggestions_pkey PRIMARY KEY (id);


--
-- Name: message_attachments message_attachments_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.message_attachments
    ADD CONSTRAINT message_attachments_pkey PRIMARY KEY (message_id, asset_id);


--
-- Name: model_cache_entries model_cache_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_cache_entries
    ADD CONSTRAINT model_cache_entries_pkey PRIMARY KEY (id);


--
-- Name: model_endpoints model_endpoints_name_key; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_endpoints
    ADD CONSTRAINT model_endpoints_name_key UNIQUE (name);


--
-- Name: model_endpoints model_endpoints_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_endpoints
    ADD CONSTRAINT model_endpoints_pkey PRIMARY KEY (id);


--
-- Name: model_fallback_entries model_fallback_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_fallback_entries
    ADD CONSTRAINT model_fallback_entries_pkey PRIMARY KEY (id);


--
-- Name: model_preferences model_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_preferences
    ADD CONSTRAINT model_preferences_pkey PRIMARY KEY (id);


--
-- Name: model_profiles model_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_profiles
    ADD CONSTRAINT model_profiles_pkey PRIMARY KEY (model_id);


--
-- Name: model_sync_runs model_sync_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_sync_runs
    ADD CONSTRAINT model_sync_runs_pkey PRIMARY KEY (id);


--
-- Name: persona_preferences persona_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.persona_preferences
    ADD CONSTRAINT persona_preferences_pkey PRIMARY KEY (id);


--
-- Name: personas personas_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_pkey PRIMARY KEY (id);


--
-- Name: retrieval_preferences retrieval_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.retrieval_preferences
    ADD CONSTRAINT retrieval_preferences_pkey PRIMARY KEY (id);


--
-- Name: retrieval_usages retrieval_usages_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.retrieval_usages
    ADD CONSTRAINT retrieval_usages_pkey PRIMARY KEY (id);


--
-- Name: tool_executions tool_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.tool_executions
    ADD CONSTRAINT tool_executions_pkey PRIMARY KEY (id);


--
-- Name: chat_messages uq_chat_message_position; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT uq_chat_message_position UNIQUE (conversation_id, "position");


--
-- Name: image_operation_inputs uq_image_operation_inputs_position; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operation_inputs
    ADD CONSTRAINT uq_image_operation_inputs_position UNIQUE (operation_id, "position");


--
-- Name: image_operation_outputs uq_image_operation_outputs_position; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operation_outputs
    ADD CONSTRAINT uq_image_operation_outputs_position UNIQUE (operation_id, "position");


--
-- Name: knowledge_chunks uq_knowledge_chunk_position; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.knowledge_chunks
    ADD CONSTRAINT uq_knowledge_chunk_position UNIQUE (document_id, "position");


--
-- Name: knowledge_documents uq_knowledge_document_content; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.knowledge_documents
    ADD CONSTRAINT uq_knowledge_document_content UNIQUE (collection_id, content_sha256);


--
-- Name: mcp_tools uq_mcp_tools_public_name; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.mcp_tools
    ADD CONSTRAINT uq_mcp_tools_public_name UNIQUE (public_name);


--
-- Name: mcp_tools uq_mcp_tools_server_name; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.mcp_tools
    ADD CONSTRAINT uq_mcp_tools_server_name UNIQUE (server_id, name);


--
-- Name: media_assets uq_media_assets_storage_key; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.media_assets
    ADD CONSTRAINT uq_media_assets_storage_key UNIQUE (storage_key);


--
-- Name: message_attachments uq_message_attachments_position; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.message_attachments
    ADD CONSTRAINT uq_message_attachments_position UNIQUE (message_id, "position");


--
-- Name: model_cache_entries uq_model_cache_endpoint_model; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_cache_entries
    ADD CONSTRAINT uq_model_cache_endpoint_model UNIQUE (endpoint_id, model_id);


--
-- Name: model_fallback_entries uq_model_fallback_model; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_fallback_entries
    ADD CONSTRAINT uq_model_fallback_model UNIQUE (model_id);


--
-- Name: model_fallback_entries uq_model_fallback_position; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_fallback_entries
    ADD CONSTRAINT uq_model_fallback_position UNIQUE ("position");


--
-- Name: tool_executions uq_tool_execution_conversation_call; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.tool_executions
    ADD CONSTRAINT uq_tool_execution_conversation_call UNIQUE (conversation_id, tool_call_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: ix_auth_sessions_user_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_auth_sessions_user_id ON public.auth_sessions USING btree (user_id);


--
-- Name: ix_chat_messages_conversation_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_chat_messages_conversation_id ON public.chat_messages USING btree (conversation_id);


--
-- Name: ix_conversations_persona_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_conversations_persona_id ON public.conversations USING btree (persona_id);


--
-- Name: ix_image_operations_assistant_message_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_image_operations_assistant_message_id ON public.image_operations USING btree (assistant_message_id);


--
-- Name: ix_image_operations_conversation_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_image_operations_conversation_id ON public.image_operations USING btree (conversation_id);


--
-- Name: ix_image_operations_user_message_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_image_operations_user_message_id ON public.image_operations USING btree (user_message_id);


--
-- Name: ix_knowledge_chunks_document_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_knowledge_chunks_document_id ON public.knowledge_chunks USING btree (document_id);


--
-- Name: ix_knowledge_documents_collection_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_knowledge_documents_collection_id ON public.knowledge_documents USING btree (collection_id);


--
-- Name: ix_mcp_tools_server_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_mcp_tools_server_id ON public.mcp_tools USING btree (server_id);


--
-- Name: ix_media_assets_content_sha256; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_media_assets_content_sha256 ON public.media_assets USING btree (content_sha256);


--
-- Name: ix_memories_persona_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_memories_persona_id ON public.memories USING btree (persona_id);


--
-- Name: ix_memory_suggestions_conversation_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_memory_suggestions_conversation_id ON public.memory_suggestions USING btree (conversation_id);


--
-- Name: ix_model_cache_entries_endpoint_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_model_cache_entries_endpoint_id ON public.model_cache_entries USING btree (endpoint_id);


--
-- Name: ix_model_sync_runs_endpoint_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_model_sync_runs_endpoint_id ON public.model_sync_runs USING btree (endpoint_id);


--
-- Name: ix_retrieval_usages_assistant_message_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_retrieval_usages_assistant_message_id ON public.retrieval_usages USING btree (assistant_message_id);


--
-- Name: ix_tool_executions_assistant_message_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_tool_executions_assistant_message_id ON public.tool_executions USING btree (assistant_message_id);


--
-- Name: ix_tool_executions_conversation_id; Type: INDEX; Schema: public; Owner: aster
--

CREATE INDEX ix_tool_executions_conversation_id ON public.tool_executions USING btree (conversation_id);


--
-- Name: auth_sessions auth_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: conversation_collections conversation_collections_collection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.conversation_collections
    ADD CONSTRAINT conversation_collections_collection_id_fkey FOREIGN KEY (collection_id) REFERENCES public.knowledge_collections(id) ON DELETE CASCADE;


--
-- Name: conversation_collections conversation_collections_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.conversation_collections
    ADD CONSTRAINT conversation_collections_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: conversation_retrieval_settings conversation_retrieval_settings_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.conversation_retrieval_settings
    ADD CONSTRAINT conversation_retrieval_settings_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: conversation_tools conversation_tools_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.conversation_tools
    ADD CONSTRAINT conversation_tools_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: conversation_tools conversation_tools_tool_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.conversation_tools
    ADD CONSTRAINT conversation_tools_tool_id_fkey FOREIGN KEY (tool_id) REFERENCES public.mcp_tools(id) ON DELETE CASCADE;


--
-- Name: conversations fk_conversations_persona_id; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT fk_conversations_persona_id FOREIGN KEY (persona_id) REFERENCES public.personas(id) ON DELETE SET NULL;


--
-- Name: image_model_profiles image_model_profiles_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_model_profiles
    ADD CONSTRAINT image_model_profiles_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.model_cache_entries(id) ON DELETE CASCADE;


--
-- Name: image_operation_inputs image_operation_inputs_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operation_inputs
    ADD CONSTRAINT image_operation_inputs_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.media_assets(id) ON DELETE RESTRICT;


--
-- Name: image_operation_inputs image_operation_inputs_operation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operation_inputs
    ADD CONSTRAINT image_operation_inputs_operation_id_fkey FOREIGN KEY (operation_id) REFERENCES public.image_operations(id) ON DELETE CASCADE;


--
-- Name: image_operation_outputs image_operation_outputs_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operation_outputs
    ADD CONSTRAINT image_operation_outputs_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.media_assets(id) ON DELETE CASCADE;


--
-- Name: image_operation_outputs image_operation_outputs_operation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operation_outputs
    ADD CONSTRAINT image_operation_outputs_operation_id_fkey FOREIGN KEY (operation_id) REFERENCES public.image_operations(id) ON DELETE CASCADE;


--
-- Name: image_operations image_operations_assistant_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operations
    ADD CONSTRAINT image_operations_assistant_message_id_fkey FOREIGN KEY (assistant_message_id) REFERENCES public.chat_messages(id) ON DELETE CASCADE;


--
-- Name: image_operations image_operations_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operations
    ADD CONSTRAINT image_operations_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: image_operations image_operations_model_cache_entry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operations
    ADD CONSTRAINT image_operations_model_cache_entry_id_fkey FOREIGN KEY (model_cache_entry_id) REFERENCES public.model_cache_entries(id) ON DELETE SET NULL;


--
-- Name: image_operations image_operations_user_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.image_operations
    ADD CONSTRAINT image_operations_user_message_id_fkey FOREIGN KEY (user_message_id) REFERENCES public.chat_messages(id) ON DELETE CASCADE;


--
-- Name: knowledge_chunks knowledge_chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.knowledge_chunks
    ADD CONSTRAINT knowledge_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.knowledge_documents(id) ON DELETE CASCADE;


--
-- Name: knowledge_documents knowledge_documents_collection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.knowledge_documents
    ADD CONSTRAINT knowledge_documents_collection_id_fkey FOREIGN KEY (collection_id) REFERENCES public.knowledge_collections(id) ON DELETE CASCADE;


--
-- Name: knowledge_documents knowledge_documents_embedding_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.knowledge_documents
    ADD CONSTRAINT knowledge_documents_embedding_model_id_fkey FOREIGN KEY (embedding_model_id) REFERENCES public.model_cache_entries(id) ON DELETE SET NULL;


--
-- Name: mcp_tools mcp_tools_server_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.mcp_tools
    ADD CONSTRAINT mcp_tools_server_id_fkey FOREIGN KEY (server_id) REFERENCES public.mcp_servers(id) ON DELETE CASCADE;


--
-- Name: memories memories_embedding_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.memories
    ADD CONSTRAINT memories_embedding_model_id_fkey FOREIGN KEY (embedding_model_id) REFERENCES public.model_cache_entries(id) ON DELETE SET NULL;


--
-- Name: memories memories_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.memories
    ADD CONSTRAINT memories_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES public.personas(id) ON DELETE CASCADE;


--
-- Name: memories memories_source_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.memories
    ADD CONSTRAINT memories_source_conversation_id_fkey FOREIGN KEY (source_conversation_id) REFERENCES public.conversations(id) ON DELETE SET NULL;


--
-- Name: memory_suggestions memory_suggestions_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.memory_suggestions
    ADD CONSTRAINT memory_suggestions_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: memory_suggestions memory_suggestions_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.memory_suggestions
    ADD CONSTRAINT memory_suggestions_persona_id_fkey FOREIGN KEY (persona_id) REFERENCES public.personas(id) ON DELETE SET NULL;


--
-- Name: message_attachments message_attachments_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.message_attachments
    ADD CONSTRAINT message_attachments_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.media_assets(id) ON DELETE CASCADE;


--
-- Name: message_attachments message_attachments_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.message_attachments
    ADD CONSTRAINT message_attachments_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.chat_messages(id) ON DELETE CASCADE;


--
-- Name: model_cache_entries model_cache_entries_endpoint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_cache_entries
    ADD CONSTRAINT model_cache_entries_endpoint_id_fkey FOREIGN KEY (endpoint_id) REFERENCES public.model_endpoints(id) ON DELETE CASCADE;


--
-- Name: model_fallback_entries model_fallback_entries_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_fallback_entries
    ADD CONSTRAINT model_fallback_entries_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.model_cache_entries(id) ON DELETE CASCADE;


--
-- Name: model_preferences model_preferences_image_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_preferences
    ADD CONSTRAINT model_preferences_image_model_id_fkey FOREIGN KEY (image_model_id) REFERENCES public.model_cache_entries(id) ON DELETE SET NULL;


--
-- Name: model_preferences model_preferences_primary_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_preferences
    ADD CONSTRAINT model_preferences_primary_model_id_fkey FOREIGN KEY (primary_model_id) REFERENCES public.model_cache_entries(id) ON DELETE SET NULL;


--
-- Name: model_preferences model_preferences_utility_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_preferences
    ADD CONSTRAINT model_preferences_utility_model_id_fkey FOREIGN KEY (utility_model_id) REFERENCES public.model_cache_entries(id) ON DELETE SET NULL;


--
-- Name: model_profiles model_profiles_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_profiles
    ADD CONSTRAINT model_profiles_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.model_cache_entries(id) ON DELETE CASCADE;


--
-- Name: model_sync_runs model_sync_runs_endpoint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.model_sync_runs
    ADD CONSTRAINT model_sync_runs_endpoint_id_fkey FOREIGN KEY (endpoint_id) REFERENCES public.model_endpoints(id) ON DELETE CASCADE;


--
-- Name: persona_preferences persona_preferences_default_persona_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.persona_preferences
    ADD CONSTRAINT persona_preferences_default_persona_id_fkey FOREIGN KEY (default_persona_id) REFERENCES public.personas(id) ON DELETE SET NULL;


--
-- Name: retrieval_preferences retrieval_preferences_embedding_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.retrieval_preferences
    ADD CONSTRAINT retrieval_preferences_embedding_model_id_fkey FOREIGN KEY (embedding_model_id) REFERENCES public.model_cache_entries(id) ON DELETE SET NULL;


--
-- Name: retrieval_usages retrieval_usages_assistant_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.retrieval_usages
    ADD CONSTRAINT retrieval_usages_assistant_message_id_fkey FOREIGN KEY (assistant_message_id) REFERENCES public.chat_messages(id) ON DELETE CASCADE;


--
-- Name: retrieval_usages retrieval_usages_chunk_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.retrieval_usages
    ADD CONSTRAINT retrieval_usages_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.knowledge_chunks(id) ON DELETE SET NULL;


--
-- Name: retrieval_usages retrieval_usages_memory_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.retrieval_usages
    ADD CONSTRAINT retrieval_usages_memory_id_fkey FOREIGN KEY (memory_id) REFERENCES public.memories(id) ON DELETE SET NULL;


--
-- Name: tool_executions tool_executions_assistant_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.tool_executions
    ADD CONSTRAINT tool_executions_assistant_message_id_fkey FOREIGN KEY (assistant_message_id) REFERENCES public.chat_messages(id) ON DELETE CASCADE;


--
-- Name: tool_executions tool_executions_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.tool_executions
    ADD CONSTRAINT tool_executions_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: tool_executions tool_executions_tool_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.tool_executions
    ADD CONSTRAINT tool_executions_tool_id_fkey FOREIGN KEY (tool_id) REFERENCES public.mcp_tools(id) ON DELETE SET NULL;


--
-- Name: tool_executions tool_executions_tool_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aster
--

ALTER TABLE ONLY public.tool_executions
    ADD CONSTRAINT tool_executions_tool_message_id_fkey FOREIGN KEY (tool_message_id) REFERENCES public.chat_messages(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict tZBQ5nodkaRVhc2bw9AE8RdSwxVWfTfKwXgbArMVbNwEoN3rx6ohcTwc7Cbatwj

