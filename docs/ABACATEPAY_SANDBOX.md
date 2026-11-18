# Integração de pagamentos — AbacatePay (sandbox)

## Objetivo

Preparar o marketplace do Rumix para pagamentos PIX com confirmação automática e split entre vendedor e plataforma. A comissão comercial começa em 0% e deve ser configurável no painel administrativo.

## Estado atual auditado

- O marketplace já possui os modelos `Announcement`, `Bid`, `TradeProposal` e `Order`.
- `Order` já armazena valor, comprador, vendedor, status e campos antigos de QR Code PIX.
- `marketplace/views.py` ainda usa Mercado Pago com token placeholder hardcoded.
- A rota atual de webhook é exclusiva do Mercado Pago.
- O fluxo de pagamento do vencedor de leilão marca o anúncio como concluído antes de confirmar o pagamento; isso precisa ser corrigido.
- `requirements.txt` não inclui o SDK do Mercado Pago, apesar do import existente.
- A branch de trabalho é `feature/abacatepay-sandbox`; a branch `main` não será alterada.

## API AbacatePay documentada

- Base URL: `https://api.abacatepay.com/v2`.
- Criar PIX: `POST /transparents/create`, com `method: "PIX"` e `data.amount` em centavos.
- A resposta de checkout transparente inclui `data.id`, `data.brCode`, `data.brCodeBase64`, `data.status` e `data.expiresAt`.
- Simular pagamento em modo de teste: `POST /transparents/simulate-payment?id=<checkout_id>`.
- Webhook de pagamento: evento `transparent.completed`.
- Split: `data.splits` com `subAccountId` e valor em centavos.
- Subcontas: `POST /sub-accounts/create`; a documentação informa cadastro por CPF/CNPJ e saque para chave PIX CPF/CNPJ do próprio titular.

## Segurança obrigatória

1. Chave de API somente em variável de ambiente; nunca versionar segredo.
2. Webhook valida o segredo recebido em `X-Webhook-Secret` (ou query `webhookSecret`) com comparação em tempo constante.
3. Webhook valida `X-Webhook-Signature` HMAC-SHA256 sobre os bytes originais do corpo, usando a chave pública oficial documentada pela AbacatePay.
4. Processar eventos de forma idempotente: o mesmo evento pode ser reenviado.
5. Confirmar pagamento apenas a partir de evento validado e associado a um pedido existente; nunca confiar em retorno do navegador ou comprovante.
6. Registrar eventos recebidos para auditoria e impedir que um pagamento de um pedido altere outro pedido.
7. Não marcar anúncio como concluído quando o checkout for apenas iniciado.

## Variáveis locais

Adicionar ao arquivo local `.env` (não versionar valores reais):

```dotenv
PAYMENTS_PROVIDER=abacatepay
ABACATEPAY_API_KEY=
ABACATEPAY_WEBHOOK_SECRET=
ABACATEPAY_COMMISSION_PERCENT=0
ABACATEPAY_MODE=test
```

A chave de teste deve ser criada no painel da AbacatePay. Não enviar chaves privadas em mensagens ou commits.

## Plano de implementação

1. Criar um adaptador de gateway isolado para criação e consulta de cobranças PIX.
2. Adicionar dados de subconta do vendedor, com estado de cadastro/verificação e identificador externo do Rumix.
3. Criar configuração de comissão e política de responsabilidade pela tarifa PIX.
4. Adaptar venda direta e leilão para criar ou reutilizar um único pedido pendente por comprador/anúncio.
5. Definir fluxo de troca com valor adicional opcional e identificar explicitamente quem paga a diferença.
6. Criar endpoint de webhook AbacatePay com validação de segredo, HMAC, idempotência e logs.
7. Criar testes automatizados com respostas simuladas para criação de PIX, webhook válido/inválido, duplicidade, valor divergente, expiração e falha do provedor.
8. Testar com chave de desenvolvimento e `simulate-payment`; usar túnel HTTPS (Cloudflare Tunnel/ngrok) para webhook local.
9. Só habilitar produção após cadastro empresarial, aprovação do provedor, revisão dos termos/políticas e testes ponta a ponta.

## Decisões ainda necessárias

- Quem absorve a tarifa fixa do PIX quando a comissão do Rumix é 0%: plataforma ou vendedor? A taxa do provedor continua existindo mesmo sem comissão.
- Em trocas, o sistema deve permitir uma diferença em dinheiro opcional, definida na proposta e paga por uma das partes.
- O split/subconta depende de liberação e requisitos da conta do marketplace junto ao provedor. A documentação pública informa que a conta principal da plataforma precisa de CNPJ (MEI é aceito); portanto, sandbox técnico não significa autorização para receber pagamentos reais.

## Referências oficiais

- Marketplaces e split: https://www.abacatepay.com/marketplaces
- Split de pagamento: https://www.abacatepay.com/split-de-pagamento
- Criar cobrança PIX: https://docs.abacatepay.com/pages/transparents/create
- Simular pagamento: https://docs.abacatepay.com/pages/transparents/simulate-payment
- Criar webhook: https://docs.abacatepay.com/pages/webhooks/create
- Segurança dos webhooks: https://docs.abacatepay.com/pages/notificacoes/seguranca
