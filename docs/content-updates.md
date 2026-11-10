# Exclusão de conteúdo, marcações e gêneros

Recordas e comentários passam a usar exclusão física nas operações do autor e da
moderação. Contas continuam com exclusão lógica. Os campos `deleted_at` dos
conteúdos permanecem para ler e filtrar registros legados. A migração não apaga
registros antigos automaticamente.

Denúncias e ações administrativas preservam os UUIDs de conteúdo excluído. As
referências históricas não têm FK para as tabelas de conteúdo. A auditoria mantém
seu trigger de imutabilidade. O detalhe administrativo retorna
`{"recorda_id": "...", "removed": true}` quando a Recorda não existe mais, e a
listagem mostra "Conteúdo removido". Notificações vinculadas ao conteúdo e aos
comentários são excluídas na mesma transação. As mídias armazenadas não são
purgadas por essa alteração.

`POST /recordas` aceita `mentioned_user_ids`, com até 20 UUIDs, deduplicados no
servidor. Somente contas ativas seguidas pelo autor e com acesso à publicação
podem ser marcadas. Perfil privado exige que a pessoa marcada também seja
seguidora aceita do autor. Cada marcação gera uma notificação. O detalhe retorna
`mentioned_users`, e a retrospectiva contabiliza as marcações de contas ativas
nas Recordas vivas do período. Marcações não concedem acesso a perfis privados.

O gênero usa o álbum da faixa do Deezer, com fallback para `/genre/{genre_id}`
quando o álbum fornece somente o ID. Não se infere gênero a partir do artista.
Se o Deezer estiver indisponível, a publicação continua sem gênero e pode ser
corrigida pelo preenchimento posterior.

## Aplicação

1. Antes de subir a versão do backend, aplicar `alembic upgrade head` no banco do
   ambiente. A revisão `0011_content_deletion_mentions` remove as FKs históricas
   e cria `recorda_mention`.
2. Para preencher gêneros ausentes nas Recordas existentes, executar
   `python scripts/backfill_song_genres.py --limit 500` no ambiente configurado.
   O limite é de faixas distintas, não de Recordas. Valores já preenchidos e
   conteúdos legados excluídos são preservados. Faixas sem metadados continuam
   pendentes e podem ser consultadas novamente. Aumentar o limite se necessário
   para alcançar faixas além das primeiras 500 pendentes.
3. Subir o frontend junto com o backend para suportar o detalhe administrativo de
   conteúdo removido e a marcação de amigos.

O downgrade recusa restaurar as FKs se houver referências a conteúdo já removido.
Isso evita apagar denúncias ou alterar a auditoria para satisfazer constraints.
Nenhum comando acima foi executado contra banco compartilhado nesta alteração;
a validação usa SQLite em memória e PostgreSQL descartável.
