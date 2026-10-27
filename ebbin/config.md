# Ebbin — configuração

Edite em Ferramentas > Ebbin > Ajustes (o botão Config do Gerenciador de add-ons abre a mesma tela, com validação). Valores fora das faixas abaixo são recusados nas Ajustes.

## Geral

- `budget_min`: meta diária de estudo, em minutos. Inteiro ou decimal de 1 a 600. Padrão 20.
- `mastered_days`: estabilidade (dias) a partir da qual um cartão é "dominado". 1 a 3650. Padrão 21.
- `rescued_r`: limiar de retrievability (0,5 a 0,99). Um cartão é "resgatado" quando a resposta é diferente de Errei (Difícil, Bom ou Fácil) e a retrievability dele, no momento da revisão, era menor que esse limiar. Padrão 0,85.
- `auto_new_per_day`: `true`/`false`. Ajusta automaticamente os cartões novos por dia dos presets do objetivo ativo (nunca de presets compartilhados com outros decks). Padrão `false`.
- `dark_theme`: tema usado no modo escuro do Anki: `"night"` (Caderno à noite) ou `"slate"` (Quadro-negro). Padrão `"night"`.
- `skin`: `true`/`false`. Visual desenhado em todo o Anki: a folha do cartão na revisão (com nível, XP total e barra de progresso do dia no topo), os botões de baixo, a lista de baralhos, a tela do baralho e a barra de cima. Só muda a aparência (CSS do add-on); os modelos de nota não são alterados. Desligado, o Anki volta ao visual padrão. Padrão `true`.

## `pomodoro`

- `focus`: minutos de foco. Inteiro de 1 a 180. Padrão 20.
- `short`: minutos da pausa curta. Inteiro de 1 a 60. Padrão 5.
- `long`: minutos da pausa longa. Inteiro de 1 a 120. Padrão 15.
- `cycles`: ciclos de foco até a pausa longa. Inteiro de 1 a 12. Padrão 4.
- `autostart`: `true`/`false`. Inicia o foco ao entrar na revisão. Padrão `false`.
- `idle_pause_s`: segundos sem responder (na revisão) até pausar o pomodoro. Inteiro de 10 a 3600. Padrão 120.

## `easy_cap`

- `enabled`: `true`/`false`. Liga o limite do botão "Fácil" (bloco em "Agendamento personalizado"). Desligado, o bloco é removido. Padrão `true`.
- `ratio`: em cartão de revisão, o Fácil não passa de Bom x `ratio` (e no mínimo Bom + 1 dia). 1,2 a 3,0. Padrão 1,5.
- `first_max_days`: teto, em dias, do Fácil em cartão novo ou aprendendo. Inteiro de 1 a 30. Padrão 4.

## `sounds`

- `enabled`: `true`/`false`. Liga os sons. Padrão `true`.
- `volume`: volume de 0 a 1. Padrão 0,8.

## `import`

- `move_after`: `true`/`false`. Move os `.txt` importados para `dest`. Padrão `true`.
- `dest`: pasta de destino dos arquivos importados (aceita `~`). Obrigatória, não pode ficar vazia. Padrão `~/Downloads/anki-importados`.
- `dupe`: tratamento de duplicados (mesmo primeiro campo e tipo de nota): `"preserve"` mantém a nota existente; `"update"` a atualiza com o conteúdo do arquivo. Padrão `"preserve"`.
