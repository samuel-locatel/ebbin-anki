# Ebbin — checklist de verificação manual

Itens que não dá para testar sem o Anki aberto. Marque cada um ao verificar.

## Antes de começar

- [ ] Faça backup: Arquivo → Criar backup. Anote o horário.
- [ ] Para testar importação, copie os `~/Downloads/lote-*.txt` para uma pasta temporária (ex.: `~/Desktop/ebbin-teste/`) e use só as cópias. Nunca os originais.
- [ ] Em Ferramentas → Ebbin → Ajustes, aponte `import.dest` (Pasta de destino) para uma pasta temporária (ex.: `~/Desktop/ebbin-destino`) e salve.
- [ ] Opcional, só se quiser testar a primeira instalação: feche o Anki, copie `ebbin/user_files/*.json` para uma pasta segura (ou use Ajustes → Exportar dados) e só então apague os originais. Para restaurar, feche o Anki e copie os arquivos de volta.

## Instalação / carregamento

- [ ] Abrir o Anki: nenhum diálogo de erro; Ferramentas mostra "Ebbin" e o clique abre a janela em Métricas.
- [ ] Se fez a instalação limpa: nível, XP e streak aparecem já calculados a partir do histórico de revisões.
- [ ] Fontes manuscritas (Caveat) e serifadas carregam na faixa, na barra e nas janelas (sem fonte padrão do sistema).
- [ ] Fechar e reabrir o Anki: nível, XP, streak, objetivos e dicas dispensadas persistem.

## Revisão (barra, sons, combo, desfazer)

- [ ] Entrar numa revisão: a barra do Ebbin aparece no topo, sem cobrir o cartão.
- [ ] Responder Bom: aparece "+XP" flutuando ~1 s e o XP da barra sobe.
- [ ] Dois acertos seguidos (Bom/Fácil): surge o combo "x1,05" (vírgula decimal); Errei zera e esconde o combo.
- [ ] Sons: Bom, Errei, Difícil, combo, subir de nível, fim de sessão e "dominado" tocam; cada um é distinto.
- [ ] Completar uma missão secundária toca o som "bom" extra.
- [ ] Desfazer (Ctrl+Z) após responder: XP e combo voltam ao valor anterior.
- [ ] Anel do pomodoro na barra avança a cada segundo; a missão principal mostra n/meta e "ótimo ponto para parar" ao cumprir.
- [ ] Sair da revisão com 9 respostas não abre pop-up; com 10 ou mais abre.

## Tela inicial (faixa, pomodoro, dicas)

- [ ] A faixa aparece acima da lista de decks, sem piscar nem perder a rolagem ao atualizar.
- [ ] Iniciar pomodoro na faixa: contagem a cada segundo sem redesenhar a lista de decks; pausar e retomar funcionam (botão "▶ mm:ss" quando pausado).
- [ ] Rodar um pomodoro completo de 20 min (ou foco de 1 min nas Ajustes): sons, sessão encerrada e pop-up ao fim; a pausa começa.
- [ ] Foco que termina durante a revisão espera a resposta atual e só depois abre o pop-up.
- [ ] Parado por mais que `idle_pause_s` na revisão: pomodoro pausa sozinho. Na tela de decks não pausa.
- [ ] Autostart ligado: entrar na revisão com o pomodoro parado o inicia.
- [ ] Abas Métricas, Objetivos e Ajustes abrem a janela Ebbin na aba certa; o botão "importar" abre a importação.
- [ ] Depois do pop-up, a faixa mostra "+N XP" por ~10 min e depois some.
- [ ] Dica dispensada (x) não volta ao atualizar a tela; o resumo semanal aparece uma vez por domingo.
- [ ] Dica FSRS aparece ao baixar o limiar (ou com ≥ 300 revisões desde a última otimização) e o botão abre as opções do deck.

## Pop-up de sessão

- [ ] Barra anima (~0,9 s) com tiques de moeda; sem nível novo mostra a barra normal, com nível novo toca o som e mostra "nível N!".
- [ ] Esc, botão "Fechar" e ✕ fecham o pop-up; um segundo pop-up com o primeiro aberto substitui o conteúdo.
- [ ] Centrado sobre a janela principal; durante a revisão não rouba o foco.
- [ ] Sons desligados ou volume 0 nas Ajustes deixam o pop-up mudo.

## Janela Ebbin (Métricas / Objetivos / Ajustes)

- [ ] Métricas com coleção real: heatmap (semanas seg a dom), gráficos e "Retenção real X% · meta Y%" fazem sentido.
- [ ] Perfil sem dados: mostra "ainda sem dados suficientes", sem erro.
- [ ] "editar" num cartão abre o navegador do Anki filtrado por esse cartão.
- [ ] Objetivos: criar, editar, ativar, arquivar (mostra resumo) e excluir (confirmação em dois passos); a faixa atualiza.
- [ ] Marcar um deck pai marca/desmarca os subdecks de forma coerente.
- [ ] Ajustes: salvar muda som e tema na revisão aberta sem reiniciar; valor inválido mostra erro em pt-BR.
- [ ] "Testar som" toca; Exportar abre o diálogo de arquivo e gera o JSON.
- [ ] Zerar (dois passos) recomeça a partir do histórico e atualiza a faixa.
- [ ] Abrir a janela pela faixa durante a revisão não rouba o foco.
- [ ] Novos por dia automático ligado com preset compartilhado: o preset não muda e a dica "autonew" aparece.

## Importação

- [ ] Ferramentas → Ebbin: importar lotes e o botão da faixa abrem o diálogo; só uma janela por vez.
- [ ] O seletor abre em `~/Downloads`: navegue até a pasta das cópias (não use os originais) e escolha os 5 arquivos, incluindo um "(1)".
- [ ] Prévia: uma linha por arquivo; o "(1)" aparece como "duplicado de ..."; rodapé mostra o impacto no orçamento e "Importar n" fica desabilitado em 0.
- [ ] Importar: notas caem nos subdecks certos; tabela de resultado por arquivo.
- [ ] Reimportar as mesmas cópias: mostra "Já existiam"; os arquivos foram movidos para o destino temporário.
- [ ] A janela não congela durante a importação; fecha ao fechar o perfil.
- [ ] Ctrl+Z após importar: confira se desfaz por arquivo (anote o comportamento).
- [ ] Ao terminar, volte `import.dest` ao padrão `~/Downloads/anki-importados` nas Ajustes e salve.

## Limite do Fácil

- [ ] Opções do deck → Agendamento personalizado: existe o bloco entre `// ebbin:start` e `// ebbin:end`; código seu fora dele está intacto.
- [ ] Cartão novo/aprendendo: o botão Fácil mostra no máximo 4 dias.
- [ ] Cartão em revisão: Fácil ≈ Bom x 1,5 (e ao menos Bom + 1 dia).
- [ ] Mudar `ratio` nas Ajustes reescreve o bloco; desligar `easy_cap.enabled` remove o bloco e os marcadores.

## Temas claro / escuro / quadro-negro

- [ ] Claro: faixa, barra, pop-up e janelas com o papel claro e terracota.
- [ ] Escuro com `dark_theme = night`: "Caderno à noite" em todas as telas.
- [ ] Escuro com `slate`: "Quadro-negro" com textura de giz; alternar o tema do Anki com a janela aberta retematiza ao vivo.
- [ ] Heatmap e gráficos legíveis nos três temas.
