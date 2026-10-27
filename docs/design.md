# Ebbin — documento de design

Add-on para Anki desktop. Gamificação, métricas, desafio dinâmico, pomodoro, importação em lote e ajuste de agendamento inspirado na curva do esquecimento de Ebbinghaus — tudo com visual desenhado à mão.

Data: 2026-10-26 · Status: rascunho para aprovação

Legenda: **[usuário]** = decidido pelo usuário · **[call]** = decisão do designer, revisável · sem marca = derivado direto da conversa/dados.

---

## 1. Intenção e porquê

O usuário estuda para concursos (hoje: CGU 2026). Um agente próprio gera 10–40 cards/dia a partir de questões e exporta `.txt`. O plano de estudo reserva **20 min/dia** para o Anki, mas a revisão consome **40 min–1 h**.

Duas dores:

1. **Não sente progresso.** Revisar parece esforço sem fim. Quer XP ganho na sessão, barra de nível subindo e streak visíveis. **[usuário]**
2. **Estoura o tempo.** Dados reais da coleção (últimos 30 dias): média **32 s por revisão** → 20 min ≈ **37 cards**. Há **325 cards novos** parados e o limite do deck é 20 novos/dia. Importar 10–40 novos/dia gera pilha de revisões que não cabe em 20 min.

Por isso a gamificação do Ebbin tem um papel duplo: **motivar e proteger o orçamento de 20 min**. Toda meta é derivada da capacidade real (orçamento ÷ tempo médio por card), não de números fixos.

Referência analisada: Synapse (AnkiWeb 236979321, instalado localmente). Ideia de XP/nível/rank/streak/desafio vem de lá, mas o desafio do Synapse é sorteado de uma lista fixa (pode pedir 150 revisões num dia com 30 pendentes) e o XP vem de tempo estudado. O Ebbin corrige as duas coisas.

## 2. Objetivos, não-objetivos, anti-objetivos

**Objetivos**
- Sentir progresso a cada sessão: XP da sessão, barra de nível, streak, cards dominados.
- Caber em 20 min: desafio dinâmico calibrado pela capacidade; pomodoro; aviso de carga futura; recompensa reduzida depois da meta.
- Intervalos coerentes: Fácil = "sei bem, mostra um pouco depois do Bom" **[usuário]**, não um salto para meses.
- Importar N `.txt` de uma vez **[usuário]** (o "Multi Deck Importer" instalado só aceita `.apkg/.zip`).
- Métricas que respondem: *quanta consistência tive? o que preciso melhorar? qual minha eficiência/produtividade?* **[usuário]**
- Objetivos (concursos) personalizáveis e trocáveis **[usuário]**.
- Experiência gostosa: visual à mão **[usuário]**, sons de jogo casual estilo Crossy Road **[usuário]**, "juice" no fim da sessão.

**Não-objetivos**
- Nada de IA **[usuário]**. Insights são regras fixas.
- Não trocar o algoritmo de agendamento: FSRS continua sendo o motor.
- Não reestilizar o conteúdo dos cards (os tipos de nota pertencem ao agente do usuário) **[call]**.
- Sem rede, sem telemetria, sem contas.
- AnkiMobile/AnkiDroid não carregam add-ons; só desktop. O usuário **só estuda no PC** **[usuário]**: XP, combo, missões e sessões são registrados ao vivo no desktop; não há reconciliação de revisões vindas de sync.

**Anti-objetivos** (se acontecer, falhou mesmo funcionando)
- O jogo empurrar o usuário para sessões de 1 h.
- Premiar acumular cards (importar não dá XP **[usuário]**).
- Punir erro (sem vidas/corações), ranking/ligas, notificações de culpa, recompensa aleatória tipo caça-níquel. **[usuário: cortou essas ideias]**
- Apertar Fácil virar estratégia para ganhar mais XP.

## 3. Contexto técnico e restrições

- Anki **26.08.1**, macOS, Qt6. Mínimo suportado: 26.08 **[call]**.
- Coleção usa **FSRS** (ligado), retenção desejada 0,90, parâmetros **padrão** (nunca otimizados), passos de aprendizado `1m 10m`, reaprendizado `10m`, 20 novos/dia, 200 revisões/dia, intervalo máx. 36500. Um único preset ("Padrão", id 1).
- `cardStateCustomizer` (agendamento personalizado) hoje vazio.
- Decks: `Concurso - CGU 2026` com ~45 subdecks por matéria (ex.: `::Programacao::JPA-Hibernate`); `Dataprev 2026 - Feito` (concurso anterior).
- Tipos de nota usados pelo agente: `Básico` (conceitos) e `IKKZ__TF.PT_BR` (certo/errado, HTML; alguns cards têm até 5 itens `T===`/`F===`).
- Tags recorrentes: `certo-errado`, `conceito`, `questao-real`, `estilo-banca`, `pegadinha`, `erro`.
- Add-ons já instalados que **sobrepõem** o Ebbin: Synapse, Pomodium, Anki Killstreaks, Pokemanki Gold, Progress Bar, Review Heatmap, Multi Deck Importer. O Ebbin não declara conflito forçado; a documentação recomenda desativar Synapse, Pomodium, Killstreaks e Progress Bar **[call]**. Deve funcionar com eles ativos sem quebrar (podem duplicar UI).
- Regra do usuário: **nunca** `git commit`/`git push`. Arquivos ficam na árvore de trabalho.
- Idioma da interface: **pt-BR** apenas **[call]**.
- Fontes embarcadas localmente (sem Google Fonts em runtime): Caveat (manuscrita) e Source Serif 4 (corpo, fallback de Iowan Old Style). Ambas OFL **[call]**.

## 4. Funcionalidades

### 4.1 Agendamento: limitar o Fácil (curva de Ebbinghaus)

Princípio: a curva do esquecimento cai rápido logo após aprender; cada revisão no momento certo achata a curva. O FSRS já modela isso (estima a probabilidade de lembrar e agenda quando cai a 90%). O Ebbin mexe em volta dele.

**Problema observado:** o usuário aperta Fácil em 63 de 140 respostas. Fácil num card novo → 6–10 dias; Fácil de novo → ~2 meses. Crescimento exponencial com o multiplicador do Fácil.

**Solução:** o Ebbin instala código no **agendamento personalizado** do Anki (`cardStateCustomizer`, JavaScript executado pelo agendador v3):
- Card em revisão (Bom e Fácil são estados de revisão): `fácil.dias = min(fácil.dias, max(bom.dias + 1, round(bom.dias × razão)))`. Razão padrão **1,5** **[usuário: "1,5–2×"; padrão 1,5 é call]**, ajustável 1,2–3,0.
- Card novo/aprendendo (Bom ainda está em passo de aprendizado, sem intervalo em dias): `fácil.dias = min(fácil.dias, teto_fácil_inicial)`, padrão **4 dias** **[call]**, ajustável.
- Nunca altera Errei/Difícil/Bom.
- Preservar qualquer código pré-existente do usuário: o bloco do Ebbin fica entre marcadores `// ebbin:start` / `// ebbin:end` e é inserido/atualizado/removido só ali.
- A regra vale para a coleção inteira (é um setting global do Anki) e sincroniza.
- **Sem correção retroativa** **[call]**: verificado em 2026-10-26, nenhum card em revisão tem intervalo > 16 dias, então só respostas futuras precisam do limite.
- Ajustes: liga/desliga, razão, teto inicial. Desligar remove o bloco.

**Lembrete de otimização do FSRS:** quando houver ≥ 300 revisões desde a última otimização (ou nunca otimizado), o Ebbin mostra na aba Hoje um aviso com botão que abre as opções do deck no ponto "Otimizar" **[call: limiar 300]**. Não otimiza sozinho.

### 4.2 Importação em lote de `.txt`

**Formato** (gerado pelo agente; é o formato nativo de importação de texto do Anki):
```
#separator:tab
#html:true|false
#notetype:IKKZ__TF.PT_BR | Básico
#tags column:N
#deck column:M
<campo1>\t<campo2>\t...\t<tags>\t<deck>
```
Arquivos em `~/Downloads`, nome `lote-<assunto>-<tipo>.txt` (ex.: `lote-hibernate-envers-certo-errado.txt`, `lote-hibernate-envers-conceitos.txt`). Existem cópias como `... (1).txt` idênticas.

**Fluxo**
1. Menu **Ferramentas → Ebbin: importar lotes .txt** (e botão na aba Hoje). Abre seletor de arquivos em `~/Downloads` com **seleção múltipla**. Também aceita escolher uma pasta (pega todos os `*.txt` dela) **[call]**.
2. **Prévia** — uma linha por arquivo: nome, tipo de nota, deck destino (do cabeçalho/coluna), nº de notas, avisos (tipo de nota inexistente, cabeçalho inválido, arquivo duplicado). Rodapé com total e **impacto no orçamento**: "esses N novos somam ~X min/dia de revisão na próxima semana" (estimativa a partir do tempo médio por card e da carga projetada; ver 4.10). Aviso apenas, nunca bloqueia.
3. **Importar** — usa o importador CSV/texto do próprio Anki (backend), respeitando cabeçalhos por arquivo. **Duplicados** (mesmo primeiro campo, mesmo tipo de nota): padrão **pular/preservar** a nota existente **[call]** — o Anki do usuário hoje está em "atualizar" (`csvDuplicateResolution = 0`), o que apagaria edições manuais se o agente regerar um card. Ajustável em Ajustes (preservar / atualizar). Um único passo de desfazer, se o backend permitir; senão, um checkpoint por lote **[deixado ao construtor]**.
4. **Resultado** — por arquivo: notas novas, atualizadas/duplicadas ignoradas, erros com linha.

**Proteções**
- Arquivos com conteúdo idêntico (hash) são importados uma vez só.
- Após importar com sucesso, mover os arquivos para `~/Downloads/anki-importados/` **[call]**, ligado por padrão, desligável.
- Importar **não dá XP** **[usuário]**.

### 4.3 XP e combo

- XP vem **só de revisar** **[usuário]**. Não vem de tempo **[call; usuário não contestou]**.
- Por resposta: **Errei 2 · Difícil 6 · Bom 10 · Fácil 10**. Fácil não vale mais que Bom **[call; usuário não contestou]**.
- **Combo:** cada Bom/Fácil seguido soma +0,05 ao multiplicador, teto **1,5×** (no 10º acerto seguido). Difícil mantém o combo sem incrementar; Errei zera **[call]**. Combo visível na barra da revisão ("×1,3" manuscrito).
- **Rendimento reduzido** (protege os 20 min) **[usuário escolheu ideia 6]**: depois que o desafio principal do dia foi cumprido **e** (um pomodoro terminou **ou** o tempo de revisão do dia passou do orçamento), o XP por resposta cai para **metade** e a barra da revisão mostra "ótimo ponto para parar". Sem bloqueio.
- Bônus fixos: desafio principal **80 + 5×nível**; cada missão secundária **30**; dia de streak **20** **[call]**.

### 4.4 Nível e rank

- XP necessário para passar do nível L: `round(400 × 1,06^(L−1))` **[call]** (~1 nível/dia no início com ~400 XP/dia, desacelerando).
- Rank a cada 5 níveis, nomes temáticos de caderno **[call]**: Rabisco (1), Rascunho (5), Esboço (10), Anotação (15), Caderno (20), Fichário (25), Apostila (30), Compêndio (35), Tratado (40), Enciclopédia (45), Biblioteca (50), **Ebbinghaus** (60).
- XP, nível e streak são **globais**, não zeram ao trocar de objetivo **[call; usuário não contestou]**.

### 4.5 Streak

- Unidade: dia do Anki (respeita o horário de virada `rollover`).
- O dia conta se: desafio principal cumprido **ou** a fila de revisões vencidas chegou a zero naquele dia.
- **Congelamento:** ganha 1 a cada 7 dias de streak, máximo 2 guardados; consumido automaticamente num dia perdido **[call]**.
- Visual: a semana em bolinhas desenhadas (feito = cheio verde, hoje = terracota, futuro = vazio), "12 dias seguidos" manuscrito.

### 4.6 Desafio dinâmico e missões do dia

**Capacidade**
- `tempo_médio` = média de `revlog.time` das revisões dos últimos 14 dias (Anki já limita o tempo por card). Sem dados: 30 s.
- `capacidade = floor(orçamento_s / tempo_médio)`. Orçamento padrão **20 min** **[usuário]**, ajustável.
- `vencidos` = revisões + aprendizado vencidos hoje, **coleção inteira** (o tempo do usuário é um só) **[call; usuário não contestou]**.

**Missão principal (desafio dinâmico)** — define streak e o bônus grande:
- Se `vencidos ≥ alvo` → "Revisar **alvo** cards" (o resto fica para amanhã).
- Se `vencidos < alvo` → "Zerar as revisões (**vencidos**) e aprender **K** novos", `K = floor((alvo − vencidos) / 3)` (card novo custa ~3 respostas no dia) **[call]**, limitado aos novos disponíveis.
- `alvo = round(capacidade × m)`. Multiplicador adaptativo `m` começa em 1,0: +0,1 após 3 dias seguidos cumpridos (máx. 1,3); −0,1 após 2 dias seguidos falhados (mín. 0,7) **[call]**.
- A meta é fixada no primeiro acesso do dia e não muda durante o dia.

**Missões secundárias (2 por dia)** **[usuário escolheu ideia 5]**, sorteadas sem repetir tipo entre dias seguidos, todas medidas pelo revlog/estado do add-on:
- Precisão: acerto do dia ≥ média de 14 dias + 3 pp (máx. 95%).
- Ritmo: tempo médio do dia ≤ 0,9 × mediana de 14 dias (mínimo de 15 respostas).
- Combo: N acertos seguidos (N = 5–15, cresce com o histórico).
- Foco: terminar 1 pomodoro completo.
- Matéria fraca: revisar ≥ 10 cards dos 2 subdecks com pior acerto.

Cumprir a principal toca **"desafio A" (chuva de moedas)**; cada secundária toca o **acerto**.

### 4.7 Volta suave

Depois de ≥ 3 dias sem revisar, os 3 dias seguintes usam `m` = 0,6 → 0,8 → 1,0 na missão principal, e a aba Hoje mostra "bem-vindo de volta" **[call; usuário aprovou a ideia]**.

### 4.8 Pomodoro

- Padrão **20 min** de foco **[usuário: orçamento]**, pausa 5, pausa longa 15 a cada 4 **[call]**. Tudo ajustável.
- Iniciar pelo botão "⏱ começar 20:00" na faixa. Opção (desligada por padrão) de iniciar sozinho ao entrar na revisão **[call]**.
- Durante a revisão: anel desenhado à mão com contagem regressiva na barra Ebbin.
- Pausa automática após **2 min** sem responder **[call]**.
- Ao terminar: toca **pomodoro A (ding-dong)**; espera o usuário responder o card atual e então abre o **pop-up de fim de sessão** (4.9). Não expulsa da revisão.
- Sessões ficam registradas (início, fim, cards, acerto, XP) para métricas e recordes.

### 4.9 Fim de sessão — pop-up A **[usuário escolheu A + B]**

Abre quando o pomodoro termina, quando a fila do deck acaba, ou quando o usuário sai da revisão — nos dois últimos casos só se houve ≥ 10 respostas na sessão **[call]**. **Sessão** = da entrada à saída da tela de revisão; um intervalo > 5 min sem responder fecha a sessão e a próxima resposta abre outra **[call]**. Com pomodoro ativo, a sessão coincide com o pomodoro. Conteúdo (ver `docs/mockups/session-summary-v2.html`, painel direito):
- **+XP da sessão** grande em terracota, contando de 0 com tique de moeda ("juice" estilo Duolingo **[usuário escolheu ideia 4]**).
- Revisões · % de acerto · duração.
- Barra de nível hachurada: parte preta = antes, parte terracota = ganho hoje; o XP "voa" até a barra. "faltam X XP p/ o nível N+1". Subir de nível toca **nível B (3 notas)**.
- Desafio cumprido (+bônus), dias seguidos (+20), **memórias resgatadas**, **novos dominados** (4.11).
- **Selo do dia** (no máximo um, por prioridade) **[call]**: *Preciso* (acerto ≥ 90%), *Relâmpago* (tempo médio ≤ 0,8 × mediana), *Resgatador* (≥ 10 memórias resgatadas), *Persistente* (≥ capacidade cards).
- **Recordes pessoais** quando batidos: mais cards num pomodoro, melhor acerto da semana, maior combo.
- Previsão de amanhã: "~N revisões previstas · cabe/não cabe nos 20 min".
- Botão preto "Fechar".

### 4.10 Tela inicial — faixa B **[usuário]**

Acima da lista de decks (ver `docs/mockups/session-summary-v2.html`, painel esquerdo):
- Abas: **Hoje · Métricas · Objetivos · Ajustes** (Hoje fica na faixa; as outras abrem a janela Ebbin) **[call: "Curva" do mockup entra dentro de Métricas]**.
- Nível + rank, barra de XP, semana do streak, missões do dia com check desenhado, objetivo ativo com contagem ("CGU 2026 · 41 dias"), botão do pomodoro.
- Carimbo "+XP" inclinado no canto após uma sessão.
- Avisos curtos: lembrete do FSRS, carga futura ("no ritmo atual você passa dos 20 min em 9/nov"), sugestão de novos de hoje (4.13).

**Barra Ebbin na revisão** **[call]**: tira fina no topo da tela de revisão, sem tocar no card: combo, "+10" flutuante a cada resposta, anel do pomodoro, progresso da missão principal.

### 4.11 Progresso que significa memória **[usuário escolheu ideia 1]**

- **Estados do card:** novo → aprendendo → firme (revisão com estabilidade FSRS < 21 d) → **dominado** (estabilidade ≥ 21 d) **[call: limiar 21 d = "maduro" do Anki]**.
- Quando um card passa a dominado: contador +1 e um "plink" (moeda +12 semitons, curta) **[call; som não escolhido pelo usuário]**.
- **Estrelas por deck/objetivo:** ★ 25%, ★★ 50%, ★★★ 80% dominados **[call]**.
- **Memórias resgatadas:** resposta ≠ Errei num card cuja probabilidade de lembrar (retrievability FSRS) no momento da revisão era < 0,85 **[call: limiar]**. Calculado ao vivo na hora da resposta (antes do Anki atualizar o estado) e gravado no log do add-on; sem retroativo.

### 4.12 Métricas **[usuário: 3 perguntas]**

Janela Ebbin, aba Métricas. Filtro: **objetivo ativo** (padrão) / tudo. Período: 30 d (padrão) / 12 sem / tudo.

**Consistência**
- Calendário de 12 semanas desenhado à mão; intensidade = minutos; marca nos dias com missão principal cumprida.
- % de dias com desafio cumprido; streak atual e recorde.
- **Aderência ao orçamento:** duração de revisão por dia vs. linha dos 20 min; "18 de 30 dias dentro do tempo".

**O que melhorar**
- Acerto por subdeck, pior → melhor, com nº de lapsos.
- Acerto e tempo por tipo/tag: `certo-errado` × `conceito`; `pegadinha` × `questao-real`.
- Cards-problema: mais lapsos; botão abre no Navegador do Anki para editar.
- Retenção real vs. desejada (0,90), com dica por regra ("abaixo da meta: rode Otimizar do FSRS" etc.).
- Acerto por hora do dia.

**Eficiência e produtividade**
- Segundos por card ao longo do tempo e por tipo de nota/nº de itens (hipótese a confirmar: cards `IKKZ__TF` com vários `T===/F===` custam 2–3×; se confirmado, dica "peça ao agente 1 item por card").
- Cards dominados por hora de estudo.
- **Projeção de carga:** revisões previstas nos próximos 30 dias vs. capacidade/dia, com o dia em que passa do orçamento. Fonte: datas de vencimento atuais + estimativa simples para novos ainda não estudados **[deixado ao construtor: método da estimativa]**.
- **Curva:** retenção média estimada da coleção hoje e ao longo do tempo, desenhada como curva de Ebbinghaus; memórias resgatadas por semana.

**Resumo semanal** (domingo, aparece uma vez na aba Hoje): cards dominados, dias de estudo, tempo médio por sessão vs. orçamento, **3 frases** geradas por regras (ex.: "Hibernate caiu 8 pp", "tempo por card caiu de 32 s para 27 s", "terça e quinta sem estudo").

### 4.13 Objetivos (concursos) **[usuário]**

- Objetivo = nome + data da prova (opcional) + decks incluídos (com subdecks).
- Vários podem existir; **um ativo**. Trocar ativa outro; o anterior vai para **arquivados** com resumo final (dominados, dias, acerto) e histórico preservado.
- O ativo define: contagem regressiva, projeção "dominados até a prova", ritmo de novos/dia para zerar o estoque de novos até a data dentro do orçamento, filtro padrão das métricas.
- Sem data: tudo funciona, sem contagem/projeção.
- **Novos por dia automático** **[call: desligado por padrão]**: quando ligado, ajusta o limite de novos do(s) preset(s) dos decks do objetivo para o que sobra do orçamento após as revisões. Desligado, a aba Hoje só mostra a sugestão ("sugestão: 14 novos hoje").
- Exemplo de dados atuais: `Concurso - CGU 2026` (ativo) e `Dataprev 2026 - Feito` (candidato a arquivado).

### 4.14 Sons **[usuário]**

Sintetizados em tempo real (Web Audio no webview do Anki), sem arquivos de áudio. Estilo "moeda/plink". Volume e liga/desliga em Ajustes. Fonte de verdade dos timbres: `docs/mockups/sounds-v2.html` (funções `S.*`). Mapeamento escolhido:

| Evento | Som (função no mockup) |
|---|---|
| Bom | `good` (moeda: triângulo f=880 → 1,5f) |
| Fácil | **igual a Bom** |
| Difícil | `hardA` (moeda 5 semitons abaixo, curta) |
| Errei | `again` (triângulo 440→370 Hz descendo, suave) |
| Combo | `comboB` — cada acerto seguido toca a moeda +1 semitom (cicla após 12) |
| Subiu de nível | `levelB` **só as 3 notas, sem a cascata** |
| Missão principal cumprida | `doneA` (chuva de moedas + acorde) |
| Pomodoro terminou | `pomoA` (ding-dong) |
| Card virou dominado | moeda +12 semitons, curta **[call]** |

No combo, a moeda do combo **substitui** a moeda simples de Bom/Fácil a partir do 2º acerto seguido **[call]**.

### 4.15 Visual **[usuário]**

Direção aprovada: mockups `session-summary-v2.html` e `dark-mode.html`, inspirados numa referência do usuário (painel de cards com papel creme, serifa, toques à mão).

- **Elementos à mão:** bordas tremidas (filtro SVG `feTurbulence` + `feDisplacementMap`), sublinhado terracota na aba ativa, marca-texto rosado atrás de rótulos manuscritos (Caveat), círculos desenhados (checks, dias), barras hachuradas, botões pretos sólidos, links sublinhados. Sem emoji, sem pauta.
- **Tipografia:** corpo serifado (Iowan Old Style → Source Serif 4 → Georgia); rótulos/numerais de destaque em Caveat; números de deck em fonte do sistema.
- **Temas** — segue o modo claro/escuro do Anki automaticamente:
  - Claro: papel `#fbfaf6`, tinta `#1f1f1f`, apagado `#7a7a74`, linha `#e3e1d9`, terracota `#cf6f55`, verde `#3f7d6a`, marca-texto `#f7ddd4`.
  - Escuro A **Caderno à noite** (padrão): papel `#1d1c1a`, tinta `#ece8df`, apagado `#9a968c`, linha `#34322e`, terracota `#e58a6f`, verde `#7fbfa6`, marca-texto `#5a3a31`.
  - Escuro B **Quadro-negro**: papel `#1f2a26`, tinta `#eef0ea`, apagado `#a7b3ac`, linha `#34433d`, terracota `#f2a08a`, verde `#a8e0c8`, marca-texto `#6b4a3f`, textura de giz nos traços.
  - Em Ajustes: escolher A ou B para o modo escuro **[usuário: manter ambos]**.
- O conteúdo dos cards não é alterado **[call]**.

### 4.16 Ajustes

Orçamento diário (min); pomodoro (foco/pausa/longa/ciclos/auto-início/pausa por inatividade); limite do Fácil (liga, razão, teto inicial); sons (liga, volume); tema escuro (A/B); mover `.txt` importados (liga, pasta); novos por dia automático (liga); limiar de "dominado" e "resgatada" (avançado); exportar/zerar dados do Ebbin (com confirmação).

## 5. Dados e arquitetura (o que já está decidido)

- **Tudo que dá para derivar do `revlog`/cards é derivado**, não duplicado (contagens, acerto, tempos, streak base).
- Estado próprio do add-on (XP/nível, combo, missões do dia, multiplicador `m`, congelamentos, sessões de pomodoro, memórias resgatadas, recordes, objetivos, selos) é **persistido por perfil** **[call]**. Onde guardar (pasta `user_files` do add-on vs. config da coleção, que sincroniza) **[deixado ao construtor]**, com a restrição: não inflar a config da coleção com logs.
- Lógica de regras (XP, capacidade, desafio, streak, selos, projeção) em módulos Python puros, sem `aqt`, testáveis com pytest. UI em webviews do Anki (faixa no deck browser, barra na revisão, janela Ebbin, pop-up).
- Nenhuma rede em runtime.
- **Primeira instalação** **[call]**: streak derivado do histórico do `revlog`; XP/nível calculados uma vez a partir das revisões existentes com valores base (2/6/10/10, sem combo nem bônus); contagem de dominados vem do estado FSRS atual. Missões, multiplicador `m`, congelamentos, recordes, selos e memórias resgatadas começam do zero. "Zerar dados" volta a esse estado inicial recalculado.

## 6. O que fica a critério do construtor

Estrutura de pastas/módulos; hooks específicos do Anki; como renderizar gráficos (SVG à mão vs. biblioteca embarcada, desde que mantenha o estilo); animações exatas; método da projeção de novos; mecanismo de desfazer da importação; local de persistência (respeitando 5); textos exatos da UI.

## 7. Escolhas do designer para o usuário revisar

1. Nome **Ebbin** (escolhido pelo usuário) · pasta `~/Developer/ebbin-anki`.
2. Só desktop, Anki ≥ 26.08, interface só pt-BR.
3. Conteúdo dos cards não é restilizado; o visual vive na faixa, barra da revisão, janela e pop-up.
4. Fácil limitado a 1,5× Bom; teto de 4 dias para Fácil em card novo/aprendendo.
5. Valores de XP (2/6/10/10), combo até 1,5×, curva de nível `400 × 1,06^(L−1)`, nomes dos ranks (último = "Ebbinghaus").
6. Congelamento de streak: 1 a cada 7 dias, máx. 2.
7. Multiplicador adaptativo do desafio (0,7–1,3) e regra "novo custa 3 respostas".
8. Pomodoro 20/5/15, pausa por inatividade 2 min, auto-início desligado.
9. "Dominado" = estabilidade ≥ 21 d; "resgatada" = retrievability < 0,85.
10. Novos por dia automático desligado por padrão (só sugestão).
11. Mover `.txt` importados para `~/Downloads/anki-importados/` ligado por padrão.
12. Recomendar desativar Synapse, Pomodium, Killstreaks e Progress Bar.
13. Importação: duplicados são pulados (nota existente preservada), ao contrário do "atualizar" atual do Anki.
14. Pop-up de fim de sessão também ao sair da revisão (≥ 10 respostas); sessão quebra após 5 min parado.
15. Na instalação, XP/nível recalculados do histórico com valores base; o resto começa do zero.
16. Sem correção retroativa de intervalos já agendados (nenhum card passa de 16 dias hoje).
