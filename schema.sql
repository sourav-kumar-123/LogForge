--
-- PostgreSQL database dump
--

\restrict ph1H6HYXDNs2SvMKSdJ9xZaVbKQxgNKC9jqy7HW2wDvsTk2MwaLDcoaUc2lGP4c

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

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
-- Name: normalized_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.normalized_logs (
    event_id character varying(36) NOT NULL,
    raw_event_id character varying(36) NOT NULL,
    schema_version character varying(20) DEFAULT '1.0'::character varying NOT NULL,
    source character varying(255) NOT NULL,
    severity character varying(10) NOT NULL,
    message text NOT NULL,
    observed_at timestamp with time zone NOT NULL,
    CONSTRAINT normalized_logs_severity_check CHECK (((severity)::text = ANY ((ARRAY['DEBUG'::character varying, 'INFO'::character varying, 'WARNING'::character varying, 'ERROR'::character varying, 'CRITICAL'::character varying])::text[])))
);


--
-- Name: raw_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_logs (
    raw_event_id character varying(36) NOT NULL,
    source_id character varying(36) NOT NULL,
    raw_event jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sources (
    source_id character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    source_type character varying(100) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: normalized_logs normalized_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_logs
    ADD CONSTRAINT normalized_logs_pkey PRIMARY KEY (event_id);


--
-- Name: raw_logs raw_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_logs
    ADD CONSTRAINT raw_logs_pkey PRIMARY KEY (raw_event_id);


--
-- Name: sources sources_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_name_key UNIQUE (name);


--
-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (source_id);


--
-- Name: idx_normalized_logs_observed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_normalized_logs_observed_at ON public.normalized_logs USING btree (observed_at DESC);


--
-- Name: idx_normalized_logs_source_severity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_normalized_logs_source_severity ON public.normalized_logs USING btree (source, severity);


--
-- Name: idx_raw_logs_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_raw_logs_source_id ON public.raw_logs USING btree (source_id);


--
-- Name: normalized_logs normalized_logs_raw_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.normalized_logs
    ADD CONSTRAINT normalized_logs_raw_event_id_fkey FOREIGN KEY (raw_event_id) REFERENCES public.raw_logs(raw_event_id);


--
-- Name: raw_logs raw_logs_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_logs
    ADD CONSTRAINT raw_logs_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(source_id);


--
-- PostgreSQL database dump complete
--

\unrestrict ph1H6HYXDNs2SvMKSdJ9xZaVbKQxgNKC9jqy7HW2wDvsTk2MwaLDcoaUc2lGP4c

