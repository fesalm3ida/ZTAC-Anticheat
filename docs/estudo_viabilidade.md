# Estudo de Viabilidade — Solução Zero Trust Anti-cheat

> **Contexto acadêmico:** análise de viabilidade da solução desenvolvida no projeto
> Zero-Trust-Syndicate (anti-cheat web para CS 1.6), cotejada com o **UltimateAntiCheat**
> (open source, user-mode) e o **Valve Anti-Cheat (VAC)**. Uso restrito ao estudo.

---

## 1. Objetivo

Este estudo avalia a **viabilidade técnica, operacional, econômica e ética** da
solução **Zero Trust Anti-cheat** construída ao longo do desenvolvimento da
aplicação (backend Flask + frontend Tailwind + scanner de memória em três
estágios), comparando-a com duas referências do mercado: o **UltimateAntiCheat**
(open source, modo usuário) e o **Valve Anti-Cheat (VAC)**, da Valve.

O objetivo é responder: **a solução é viável para o propósito a que se
destina** — detecção didática de cheats client-side em laboratório — e quais
são suas fronteiras frente a soluções comerciais.

---

## 2. O modelo Zero Trust aplicado ao anti-cheat

O princípio **Zero Trust** ("nunca confie, sempre verifique") parte da premissa
de que nenhum elemento é confiável por padrão — inclusive o próprio cliente do
jogador, que é justamente o elo onde o cheat atua.

A solução desenvolvida materializa esse princípio no **endpoint**:

- **Não confia no cliente**: em vez de assumir que o processo do jogo está
  íntegro, o anti-cheat **verifica ativamente** seu estado.
- **Verificação contínua e multi-evidência**: três estágios independentes
  (módulos injetados, integridade/hooks do `opengl32.dll`, artefatos e strings em
  memória) alimentam um veredito auditável com pontuação de ameaça.
- **Somente leitura**: o verificador observa (não injeta, não modifica), o que
  preserva a integridade do processo auditado.

É importante delimitar: trata-se de um **componente de verificação de endpoint**
inspirado no modelo Zero Trust, e não de uma arquitetura Zero Trust completa —
esta exigiria também um lado servidor (a detecção *server-side* permanece como
trabalho futuro, conforme a seção 6).

---

## 3. Panorama de soluções comparáveis

### 3.1 UltimateAntiCheat

O UltimateAntiCheat, por ser **open source** e operar em **modo usuário
(user-mode)**, apresenta como principal vantagem a **transparência** e a
possibilidade de **estudo e modificação do código-fonte**. Isso o torna adequado
para **fins educacionais e prototipagem**. No entanto, sua **segurança é
limitada**, sendo mais suscetível a **técnicas de bypass**, especialmente contra
cheats mais avançados que operam em nível de **kernel**. Dessa forma, seu uso em
**ambientes de produção** torna-se restrito (ALSCH092, [2023]).

### 3.2 Valve Anti-Cheat (VAC)

O Valve Anti-Cheat (VAC) é uma solução amplamente utilizada e reconhecida por
sua **escalabilidade** e **baixo impacto em performance** (VALVE CORPORATION,
2003). Seu modelo de detecção baseado em **assinaturas e heurísticas**, aliado ao
sistema de **banimento tardio (delayed bans)**, permite identificar comportamentos
suspeitos sem alertar imediatamente o usuário. Contudo, sua principal limitação
está na **complexidade de impedir cheats em tempo real**, uma vez que o banimento
é tardio e o modelo é predominantemente **reativo** (VALVE CORPORATION, 2003).

### 3.3 Síntese do panorama

| Solução | Licença/modo | Vantagem central | Limitação central | Indicação |
|---|---|---|---|---|
| **UltimateAntiCheat** | Open source, user-mode (C++/Windows) | Transparência, estudo e modificação | Bypass por cheats em kernel-mode | Educação e prototipagem |
| **Valve Anti-Cheat (VAC)** | Proprietária, integrada à Steam | Escala e baixo overhead; banimento tardio | Reativa; não impede em tempo real | Produção em larga escala |
| **Zero Trust (nossa)** | Acadêmica, externa e somente leitura | Evidência multiestágio e auditável | Client-side; assinaturas estáticas | Ensino/laboratório |

---

## 4. Avaliação da solução desenvolvida

### 4.1 Viabilidade técnica

A solução **foi implementada e validada** durante o desenvolvimento da aplicação:

| Item entregue | Situação |
|---|---|
| Autenticação (login/registro, sessão, hash) | Funcional e testado |
| Dashboard e API REST | Funcional (login, processos, scan, histórico) |
| Scanner em 3 estágios (A módulos, B detours/PE, C artefatos/strings) | Implementado; Estágio B com parser de PE próprio (PE32/PE64) |
| Backend duplo (real no Windows / demo fora dele) | Funcional e testado |
| Banco autocurativo (SQLite) | Elimina falhas de esquema em execução |
| Tratamento de processo ausente | Emite aviso explícito, sem falso resultado |

Nos cenários de teste, a varredura classificou corretamente o processo com o
cheat v8 injetado como `HACKEADO` (score máximo) e o processo íntegro como
`LIMPO` (score zero), além de emitir o aviso quando o jogo não estava em
execução. Portanto, a **viabilidade técnica está comprovada** para o escopo
didático.

### 4.2 Viabilidade operacional

- **Requisito de plataforma:** o scan real depende do **Windows** e de
  privilégios equivalentes aos do jogo (leitura de memória de outro processo).
- **Operação simples:** a interface web centraliza seleção de processo,
  execução da varredura, veredito e histórico, sem exigir linha de comando.
- **Escopo de uso:** adequada a **laboratório**, offline contra bots; não
  pressupõe operação em servidores públicos com anti-cheat concorrente.

### 4.3 Viabilidade econômica

- **Custo de licenças ~zero**: a stack é integralmente gratuita e de código
  aberto (Python, Flask, SQLite, Tailwind, bibliotecas da stdlib).
- **Sem dependências pagas** de SDK ou serviços de terceiros.
- **Custo real** concentrado em **esforço de desenvolvimento** e em uma
  infraestrutura mínima (um host Windows para testes).
- Comparativamente, é economicamente **equivalente ao UltimateAntiCheat**
  (open source) e **muito inferior** ao custo de licenciar/operar soluções
  proprietárias de larga escala.

### 4.4 Viabilidade legal e ética

- O artefato tem **finalidade defensiva e acadêmica**; o scanner é **externo e
  somente leitura** (não injeta, não modifica o processo).
- Recomenda-se execução em **ambiente de laboratório, offline contra bots**,
  evitando partidas protegidas por anti-cheats de terceiros.
- Sob essas condições, a solução é **viável e aderente ao propósito** do estudo.

### 4.5 Riscos e limitações

| Risco/limitação | Impacto | Mitigação possível |
|---|---|---|
| Detecção **client-side** | Não cobre cheats que evitam o processo | Complementar com detecção server-side |
| **Assinaturas estáticas** | Cheats ofuscados/renomeados escapam | Assinaturas atualizáveis (YAML/JSON) |
| **Falsos positivos** no Estágio B | Divergência disco×memória isolada | Priorizar `mem[0]=0xE9` como evidência forte |
| Dependência de **privilégios** | Falha ao abrir o processo | Execução elevada / documentação |
| **Bypass** por user-mode | Como no UltimateAntiCheat | Escopo acadêmico; não é produto de produção |

---

## 5. Análise comparativa

| Critério | **Zero Trust (nossa)** | **UltimateAntiCheat** | **VAC** |
|---|---|---|---|
| **Licença** | Acadêmica (código do estudo) | Open source | Proprietária |
| **Modo de operação** | Externo, somente leitura | User-mode (in-process) | Integrado à Steam |
| **Detecção** | 3 estágios + veredito/score | Módulos, memória, debug, assinatura | Assinaturas + heurísticas |
| **Escalabilidade** | Baixa (didática) | Baixa/média | Alta |
| **Transparência** | Alta (código aberto do estudo) | Alta | Baixa |
| **Resistência a bypass** | Limitada | Limitada (user-mode) | Média/alta (escala e sigilo) |
| **Tempo real** | Sim (verificação pontual) | Sim | Reativa (delayed bans) |
| **Custo** | ~zero | ~zero | Licenciado pela plataforma |
| **Melhor uso** | Ensino/laboratório | Prototipagem/estudo | Produção em larga escala |

---

## 6. Parecer de viabilidade

A solução **Zero Trust Anti-cheat é viável** para o propósito a que se propõe:

- ✅ **Tecnicamente viável** — implementada, testada e com detecção correta nos
  cenários avaliados.
- ✅ **Economicamente viável** — stack gratuita, sem licenças ou SDKs pagos.
- ✅ **Operacionalmente viável** — interface web simples, em ambiente de
  laboratório.
- ✅ **Ética e legalmente adequada** — escopo defensivo, somente leitura.

**Ressalva:** a solução **não substitui** um anti-cheat de produção como o VAC.
Ela é, por natureza, **client-side e reativa em relação a assinaturas**, com as
mesmas fragilidades estruturais do UltimateAntiCheat frente a cheats em
kernel-mode. Sua posição mais adequada é a de **componente educacional e de
verificação de endpoint**, que idealmente se soma a uma camada **server-side**
(heurísticas comportamentais: snap de mira, linha de visão, variância de
tracking) para compor uma defesa em profundidade — coerente com o princípio Zero
Trust de **nunca confiar apenas em um único ponto de verificação**.

**Conclusão:** viável para os fins do estudo; **não recomendada** como solução
única de proteção em produção.

---

## 7. Referências

1. ALSCH092. **UltimateAntiCheat**: open source usermode anti-cheat system (C++, Windows). GitHub, [2023]. Disponível em: <https://github.com/AlSch092/UltimateAntiCheat>. Acesso em: 17 out. 2026.
2. VALVE CORPORATION. **Valve Anti-Cheat (VAC)**: sistema anti-cheat e banimentos de jogo. [S.l.]: Valve Corporation, 2003. Disponível em: <https://partner.steamgames.com/doc/features/anticheat>. Acesso em: 17 out. 2026.
3. ZERO-TRUST-SYNDICATE. **Anti-cheat v8: detecção client-side das técnicas do laboratório**. [S.l.: s.n.], 2026. Disponível em: `rebuild/v8/ANTICHEAT-v8.md`. Acesso em: 17 out. 2026.
4. ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 6023: informação e documentação — referências — elaboração**. Rio de Janeiro: ABNT, 2018. 68 p.
5. MICROSOFT. **ReadProcessMemory function (memoryapi.h)**. 2024. Disponível em: <https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory>. Acesso em: 17 out. 2026.
