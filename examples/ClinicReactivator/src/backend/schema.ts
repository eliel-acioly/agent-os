/**
 * SCHEMA RELACIONAL (Drizzle / PostgreSQL) — AGENT-OS
 */
import { pgTable, text, timestamp, uuid, numeric, integer } from 'drizzle-orm/pg-core';

export const clientes = pgTable('clientes', {
  id: uuid('id').primaryKey().defaultRandom(),
  nome: text('nome').notNull(),
  whatsapp: text('whatsapp').notNull().unique(),
  status: text('status').default('ATIVO').notNull(),
  criadoEm: timestamp('criado_em').defaultNow().notNull()
});

export const oportunidades = pgTable('oportunidades', {
  id: uuid('id').primaryKey().defaultRandom(),
  clienteId: uuid('cliente_id').references(() => clientes.id, { onDelete: 'cascade' }).notNull(),
  acaoRecomendada: text('acao_recomendada').notNull(),
  valorPotencialBrl: numeric('valor_potencial_brl').notNull(),
  status: text('status').default('ABERTA').notNull(),
  criadoEm: timestamp('criado_em').defaultNow().notNull()
});
