--
-- PostgreSQL database dump
--

-- Dumped from database version 14.18 (Homebrew)
-- Dumped by pg_dump version 14.18 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: individual_groups; Type: TABLE DATA; Schema: public; Owner: ppl_user
--

INSERT INTO public.individual_groups (id, name, description, created_by, created_at, updated_at, member_count, member_ids, visibility, tags, cover_individual_id, metadata) VALUES ('grp_9e3fd3d2995f', 'VIP Customers', 'Updated: High-value customers across all stores', 'default_user', '2025-12-17 09:31:23.446095+02', '2025-12-19 10:52:01.138915+02', 3, '{27627db6-71bb-4ee5-a6d8-883a3bc35aab,b24ad688-26f0-4e1e-9484-4fecec18df9c,387d46ac-f5a9-403a-b127-2a82d6fc61fd}', 'private', '{vip,loyalty,premium}', NULL, '{}');
INSERT INTO public.individual_groups (id, name, description, created_by, created_at, updated_at, member_count, member_ids, visibility, tags, cover_individual_id, metadata) VALUES ('grp_57b0c55aeef9', 'Group A', 'This is Group A', 'default_user', '2026-03-01 11:31:29.681276+02', '2026-03-04 10:06:11.662082+02', 2, '{cbf5fb63-6771-4bdc-97d4-856156e646e4,af89b49c-23b0-4719-96ca-0362f142392d}', 'private', '{}', NULL, '{}');


--
-- Data for Name: group_memberships; Type: TABLE DATA; Schema: public; Owner: ppl_user
--

INSERT INTO public.group_memberships (id, group_id, individual_id, added_by, added_at, notes) VALUES ('mem_e7a02a7cb823', 'grp_9e3fd3d2995f', '27627db6-71bb-4ee5-a6d8-883a3bc35aab', 'default_user', '2025-12-18 06:35:27.54597+02', NULL);
INSERT INTO public.group_memberships (id, group_id, individual_id, added_by, added_at, notes) VALUES ('mem_20f363b60826', 'grp_9e3fd3d2995f', 'e47fe54a-8fb4-4e38-b68e-2d3134dec7f8', 'default_user', '2025-12-18 06:50:15.464476+02', NULL);
INSERT INTO public.group_memberships (id, group_id, individual_id, added_by, added_at, notes) VALUES ('mem_09be454debca', 'grp_57b0c55aeef9', '23bda2de-d057-4801-8f4d-55b1dcc46d99', 'default_user', '2026-03-04 08:06:11.667452+02', NULL);


--
-- PostgreSQL database dump complete
--

