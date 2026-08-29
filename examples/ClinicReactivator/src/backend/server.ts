import express from 'express';
import cors from 'cors';
import { MetricasPerformanceDTO, OportunidadeReceitaDTO } from '../../shared/contracts/types';

const app = express();
app.use(cors());
app.use(express.json());

// Endpoint de Métricas Executivas
app.get('/api/metrics', (req, res) => {
  const metrics: MetricasPerformanceDTO = {
    totalClientesAtivos: 184,
    receitaRecuperadaMesBrl: 14250.00,
    taxaConversaoPercent: 28.4,
    oportunidadesAbertas: 6
  };
  res.json({ success: true, metrics });
});

// Endpoint de Oportunidades
app.get('/api/opportunities', (req, res) => {
  const opps: OportunidadeReceitaDTO[] = [
    {
      id: 'opp-1',
      clienteNome: 'Mariana Silva',
      contatoWhatsapp: '+5511988887777',
      acaoSugerida: 'Enviar oferta VIP de retorno com 15% de bônus',
      potencialRetornoBrl: 450.00,
      urgenciaHoras: 12,
      status: 'ABERTA'
    }
  ];
  res.json({ success: true, opportunities: opps });
});

app.listen(3000, () => console.log('🚀 Server running on port 3000'));
