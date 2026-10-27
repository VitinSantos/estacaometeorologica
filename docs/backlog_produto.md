# Backlog do produto (Scrum)

**Produto:** ClimaSP Aberta, estação meteorológica inteligente.
**Equipe:** preencher com nomes e papéis (Product Owner, Scrum Master, desenvolvedores).
**Entrega final da documentação:** 14/11. Entregas parciais no calendário da disciplina: 11/08, 25/08, 08/09, 22/09, 06/10, 20/10 e 03/11.

## Requisitos

**Funcionais**
- RF01: o ESP32 envia leituras de temperatura, umidade, pressão, qualidade do ar, luminosidade e chuva.
- RF02: o servidor valida e trata leituras inconsistentes.
- RF03: o servidor armazena as leituras recentes em memória (sem banco de dados, por simplicidade).
- RF04: o cidadão vê as condições atuais num dashboard público.
- RF05: o cidadão vê o histórico de 24 horas.
- RF06: o cidadão vê as estações num mapa e descobre a mais próxima.

**Não funcionais**
- RNF01: só o ESP32 autorizado grava dados (chave de API).
- RNF02: o dashboard funciona em celular e computador.
- RNF03: o dashboard é acessível (contraste, leitor de tela, teclado).
- RNF04: nenhum segredo no repositório.

## Histórias de usuário

| ID | História | Prioridade | Pontos | Status |
|---|---|---|---|---|
| H01 | Como cidadão, quero ver a temperatura e a umidade atuais para decidir como me vestir. | Essencial | 3 | Pronta |
| H02 | Como cidadão, quero ver a qualidade do ar para saber se posso me exercitar ao ar livre. | Essencial | 3 | Pronta |
| H03 | Como cidadão, quero ver quanto choveu nas últimas 24 h. | Essencial | 5 | Pronta |
| H04 | Como gestor urbano, quero o histórico de 24 h para identificar tendências. | Importante | 5 | Pronta |
| H05 | Como cidadão, quero saber a estação mais próxima de mim. | Importante | 3 | Pronta |
| H06 | Como equipe, queremos que leituras absurdas sejam descartadas para não poluir os dados. | Essencial | 5 | Pronta |
| H07 | Como equipe, queremos testar o sistema sem o hardware, usando um simulador. | Importante | 2 | Pronta |
| H08 | Como equipe, queremos o firmware lendo todos os sensores e enviando por HTTPS. | Essencial | 8 | Código pronto, falta testar no hardware |
| H09 | Como equipe, queremos montar o circuito com divisores de tensão corretos. | Essencial | 5 | A fazer (depende da compra) |
| H10 | Como equipe, queremos calibrar o pluviômetro e o MQ-135. | Importante | 5 | A fazer |
| H11 | Como equipe, queremos publicar o sistema na Vercel. | Essencial | 3 | Em andamento (site no ar, falta o redeploy com a chave) |
| H12 | Como equipe, queremos a documentação final entregue. | Essencial | 5 | Em andamento |
| H13 | Como gestor, quero alertas de chuva forte ou ar ruim. | Futuro | 8 | Não iniciada |
| H14 | Como equipe, queremos limitar a taxa de requisições da API. | Futuro | 3 | Não iniciada |
| H15 | Como equipe, queremos conferir o certificado do servidor no firmware. | Futuro | 3 | Não iniciada |
| H16 | Como gestor, quero histórico permanente das leituras (banco de dados). | Futuro | 5 | Não iniciada |

## MVP

H01 a H08, H11 e H12.

## Plano das sprints restantes

Preencha as sprints anteriores com o que a equipe realmente fez. As duas últimas, a partir de 24/10:

| Sprint | Período | Meta | Histórias |
|---|---|---|---|
| Sprint 7 | 24/10 a 03/11 | Sistema no ar e hardware montado | H11, H09, H08 (teste no hardware) |
| Sprint 8 | 04/11 a 14/11 | Calibração, testes finais e documentação | H10, H12 |

## Definição de pronto

Uma história está pronta quando: o código foi revisado, os testes passam, funciona no celular e no computador, não expõe segredos e está documentada.

## Riscos

| Risco | Mitigação |
|---|---|
| Atraso na chegada dos componentes | simulador permite validar o software enquanto isso |
| Módulo vendido como BMP280 ser BME280 | documentado em `ligacoes_hardware.md` |
| Danificar o ESP32 com 5 V | divisores de tensão no MQ-135 e no ECHO |
| MQ-135 sem calibração dar valores enganosos | índice relativo, documentado como não oficial |
| Servidor reiniciar e apagar o histórico da memória | decisão consciente (sem banco); o ESP32 reenvia a cada 60 s; documentado no README |
| Vazamento da chave de API | `.gitignore`, variáveis de ambiente e troca da chave se necessário |
