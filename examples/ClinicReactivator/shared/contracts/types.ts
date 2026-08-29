/**
 * CONTRATOS COMPARTILHADOS (SSOT) — AGENT-OS
 */

export interface RegistroAtividadeDTO {
  id: string;
  clienteId: string;
  canalOrigem: 'WHATSAPP' | 'WEB' | 'API';
  status: 'PENDENTE' | 'PROCESSADO' | 'CONCLUIDO';
  valorBrl?: number;
  criadoEm: string;
}

export interface OportunidadeReceitaDTO {
  id: string;
  clienteNome: string;
  contatoWhatsapp: string;
  acaoSugerida: string;
  potencialRetornoBrl: number;
  urgenciaHoras: number;
  status: 'ABERTA' | 'EXECUTADA' | 'DESCARTADA';
}

export interface MetricasPerformanceDTO {
  totalClientesAtivos: number;
  receitaRecuperadaMesBrl: number;
  taxaConversaoPercent: number;
  oportunidadesAbertas: number;
}
