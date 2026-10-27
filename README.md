# Ebbin

Add-on do Anki (>= 26.08) com gamificação (XP, nível, combo, missões), métricas, pomodoro, limite do botão "Fácil" (curva de Ebbinghaus) e importação em lote de arquivos `.txt`. Interface somente em pt-BR, sem rede e sem IA. Especificação completa: `docs/design.md`.

## Instalação (link simbólico)

Crie o link simbólico no diretório de add-ons do Anki:

```
ln -s ~/Developer/ebbin-anki/ebbin ~/Library/Application\ Support/Anki2/addons21/ebbin
```

Abra o Anki: o menu Ferramentas deve mostrar "Ebbin", sem diálogo de erro.

## Desenvolvimento

Crie o ambiente virtual com o Python 3.13 que acompanha o Anki:

```
"$HOME/Library/Application Support/AnkiProgramFiles/python/cpython-3.13.5-macos-aarch64-none/bin/python3.13" -m venv .venv
.venv/bin/pip install anki==26.8.1 aqt==26.8.1 pytest
```

Testes:

```
.venv/bin/pytest -q
node --test tests/js/
```

Regras: `ebbin/core` não importa `anki` nem `aqt`; `ebbin/data` pode importar `anki`; só `ebbin/ui` importa `aqt`. A verificação manual na interface está em `docs/manual-checklist.md`.

## Add-ons recomendados para desativar

Fazem coisas parecidas e podem duplicar a interface: **Synapse**, **Pomodium**, **Anki Killstreaks** e **Progress Bar**. O Ebbin funciona com eles ativos, mas é melhor desativá-los.

## Onde ficam os dados

Cada perfil do Anki tem seu próprio estado em `ebbin/user_files/<perfil>.json` (por exemplo `ebbin/user_files/Usuário 1.json`): XP, nível, streak, missões, objetivos, sessões e dicas dispensadas. O que dá para derivar do histórico de revisões do Anki é recalculado, não duplicado. Ajustes > Exportar copia esse arquivo; Ajustes > Zerar apaga e recomeça a partir do histórico. Para testar uma instalação limpa (opcional), primeiro faça cópia: com o Anki fechado, copie `ebbin/user_files/*.json` para uma pasta segura (ou use Ajustes → Exportar dados); só então apague os originais. O estado tem objetivos, sessões e missões que não dá para recalcular do histórico. Para restaurar, feche o Anki e copie os arquivos de volta para `ebbin/user_files/`.

As opções ficam em `ebbin/config.json` (ou nas Ajustes do Ebbin). Descrição de cada chave: `ebbin/config.md`.

## Limite do "Fácil" e "Agendamento personalizado"

O Ebbin não altera cartões nem modelos de nota. O limite do Fácil é aplicado pelo recurso "Agendamento personalizado" (Custom scheduling) das opções de deck do Anki, que guarda um trecho de JavaScript na coleção.

- O bloco do Ebbin fica entre os marcadores `// ebbin:start` e `// ebbin:end`. Só esse trecho é inserido, atualizado ou removido; qualquer código seu fora dos marcadores é preservado.
- Ao desativar `easy_cap.enabled`, o bloco inteiro (marcadores incluídos) é removido.
- Alterar `ratio` ou `first_max_days` nas Ajustes reescreve o bloco.
- Antes de desativar/remover o Ebbin, desligue o Limite do Fácil em Ajustes (o bloco fica no Agendamento personalizado do Anki).

## Novos por dia automático

Com `auto_new_per_day` ligado, o Ebbin ajusta o limite de cartões novos por dia dos presets dos decks do objetivo ativo, no máximo uma vez por dia do Anki. Presets compartilhados com outros decks (fora do objetivo) nunca são alterados: nesse caso o Ebbin pula o ajuste e mostra uma dica na faixa. Desligado, apenas sugere o valor.
