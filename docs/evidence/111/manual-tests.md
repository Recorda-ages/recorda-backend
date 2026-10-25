# Três testes manuais — issue #111

Ambiente: API real em `http://127.0.0.1:8011/docs`, com SQLite descartável e contas de exemplo. Nenhuma conta real é utilizada. Execute os testes na ordem abaixo. Se a prévia reiniciar, os dados serão recriados e será necessário começar novamente.

**Demonstração realizada em 21/10/2026:** os três cenários foram executados pelo Codex no Swagger a pedido do usuário, que acompanhou a execução e autorizou incluir os resultados no PR. Consulte o [registro com capturas e respostas](guided-demo.md). A execução independente pelo usuário não foi declarada.

## Preparação

Abra o Swagger e, em um PowerShell, carregue as contas da prévia:

```powershell
cd C:\Users\Usuario\Documents\GitHub\Recorda\recorda-backend
$demo = Get-Content ..\tmp\preview-111-session.json -Raw | ConvertFrom-Json
$demo | Select-Object owner_id, recorda_id | Format-List
```

Para trocar a conta no Swagger, copie o token desejado com um destes comandos:

```powershell
# Dono da conta: demo_owner
Set-Clipboard $demo.owner_token

# Solicitante/seguidor 1: demo_sender1
Set-Clipboard $demo.sender_tokens[0]

# Solicitante/visitante 2: demo_sender2
Set-Clipboard $demo.sender_tokens[1]
```

Execute somente o comando da conta que vai usar naquele momento. No Swagger, clique em **Authorize**. Se houver uma conta autorizada, clique em **Logout**; cole o token em **Value**, sem escrever `Bearer`, clique em **Authorize** e depois **Close**. Os tokens são exclusivos desta prévia.

Em cada operação, clique em **Try it out**, preencha os parâmetros/corpo e clique em **Execute**. Confira **Server response**, pois **Example Value** é apenas a documentação.

O `user_id` usado nos endpoints de follow, grid e listas é o `owner_id` exibido na preparação. O `recorda_id` é o outro identificador exibido. Se precisar copiar sem digitar:

```powershell
Set-Clipboard $demo.owner_id
# Ou, para o detalhe da Recorda:
Set-Clipboard $demo.recorda_id
```

## 1. Salvar e consultar a privacidade

**Conta: demo_owner.**

1. Execute `GET /api/v1/users/me/settings`. Na prévia atual, deve retornar 200, `is_private: true` e `language: "pt-BR"`.
2. Execute `PATCH /api/v1/users/me/settings` com:

   ```json
   { "is_private": false }
   ```

3. Confira 200, `is_private: false`, `language: "pt-BR"` e `accepted_requests: 0`. Os dois seguidores da captura anterior já foram aceitos.
4. Execute novamente o GET: deve continuar `false`, comprovando a persistência.
5. Execute PATCH com `{"is_private": true}` e consulte o GET novamente: deve retornar `true`, mantendo `language: "pt-BR"`.

**Evidência:** captura do GET final e da resposta do PATCH. Anote se o idioma permaneceu igual.

## 2. Tornar pública aceita os pedidos e notifica os solicitantes

**Comece com demo_owner privado, como no final do teste 1.**

1. Autorize **demo_sender1**. Execute `DELETE /api/v1/users/{user_id}/follow` usando o ID de demo_owner; isso remove o vínculo da demonstração anterior. Em seguida, execute `POST /api/v1/users/{user_id}/follow` para o mesmo ID. Deve retornar 200 com `follow_status: "solicitado"`.
2. Autorize **demo_sender2** e repita DELETE e POST. O POST também deve retornar `"solicitado"`.
3. Autorize **demo_owner** e execute `GET /api/v1/notifications`. Anote o `follow_id` de cada uma das duas novas notificações `FOLLOW_REQUEST`.
4. Execute PATCH de configurações com `{"is_private": false}`. Deve retornar 200 e **`accepted_requests: 2`**.
5. Consulte as notificações de demo_owner: aquelas duas solicitações, com os mesmos `follow_id`, devem agora ser `NEW_FOLLOWER`.
6. Autorize cada solicitante e consulte `GET /api/v1/notifications`: cada um deve ter uma nova `FOLLOW_ACCEPTED` referente ao seu pedido.
7. Autorize demo_owner e repita o PATCH `false`: deve retornar `accepted_requests: 0`, sem criar novos avisos de aceite para aqueles pedidos.

Pode haver notificações antigas da captura anterior. Compare os `follow_id` anotados, não apenas o total de avisos.

**Evidência:** captura do PATCH com 2 aceites e de uma `FOLLOW_ACCEPTED` com o `follow_id` correspondente. Anote também o resultado da repetição: 0.

## 3. Conteúdo antigo acompanha a privacidade sem remover seguidores

**Comece com demo_owner público e ambos os solicitantes aceitos, como no final do teste 2.**

1. Autorize **demo_sender2** e execute DELETE do follow de demo_owner. Essa conta será o visitante sem vínculo; demo_sender1 continuará sendo seguidor.
2. Ainda como demo_sender2, consulte:
   - `GET /api/v1/recordas/{recorda_id}` usando a Recorda já existente;
   - `GET /api/v1/users/{user_id}/recordas` usando o ID de demo_owner;
   - `GET /api/v1/users/{user_id}/followers` usando o mesmo ID.

   As três chamadas devem retornar **200**, pois a conta está pública. O grid deve conter a Recorda indicada.
3. Autorize **demo_owner** e faça PATCH com `{"is_private": true}`.
4. Autorize **demo_sender2** e repita aquelas três chamadas: todas devem retornar **403**.
5. Autorize **demo_sender1** e repita: todas devem retornar **200**. Isso confirma que o seguidor aceito foi preservado.
6. Autorize **demo_owner** e faça PATCH com `{"is_private": false}`. Volte para demo_sender2 e repita as três leituras: devem voltar a **200**, sem recriar a Recorda nem seguir a conta.

**Evidência:** captura do detalhe negado para demo_sender2 (403), do mesmo detalhe permitido para demo_sender1 (200) e, se possível, do detalhe reaberto para demo_sender2 (200).

O feed geral também tem critérios de afinidade musical; ele foi coberto nos testes automatizados com fixtures próprios e não faz parte deste roteiro manual simplificado.

## Modelo para uma nova execução independente

Preencha após executar:

```text
Teste 1 — passou/falhou:
Resultado observado:

Teste 2 — passou/falhou:
accepted_requests na primeira execução:
accepted_requests na repetição:
Notificações conferidas:

Teste 3 — passou/falhou:
Visitante: pública ___ / privada ___ / pública novamente ___
Seguidor aceito com conta privada: ___

Ambiente: Swagger local, SQLite descartável, contas de exemplo.
Capturas anexadas:
```
