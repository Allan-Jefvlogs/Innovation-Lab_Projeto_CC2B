# Spec Delta: integração de usuários

## ADDED Requirements

### Requirement: Usuário pode alterar voluntariamente a própria senha

O usuário autenticado MUST poder alterar somente a própria senha mediante validação da senha atual, confirmação coincidente e política de senha existente. A identidade-alvo MUST vir do contexto autenticado no backend; a operação MUST NOT aceitar um identificador arbitrário de usuário. O backend MUST usar o armazenamento nativo seguro de senha, MUST rejeitar a repetição da senha atual e MUST NOT retornar nem registrar senhas ou hashes.

#### Scenario: Validação e gravação confirmada
- **WHEN** o usuário autenticado informa senha atual válida, nova senha conforme a política e confirmação coincidente
- **THEN** o backend grava a nova senha do usuário autenticado e a resposta contém somente confirmação sanitizada
- **AND** o frontend encerra a sessão local e exige novo login.

#### Scenario: Rejeitar dados inválidos
- **WHEN** a senha atual está incorreta, a confirmação diverge, a política falha ou a nova senha é igual à atual
- **THEN** o backend rejeita a operação sem alterar a senha armazenada
- **AND** a resposta não inclui valores de senha, hash ou detalhes sensíveis.

#### Scenario: Não permitir alterar outra conta
- **WHEN** uma requisição tenta escolher a conta-alvo por parâmetro fornecido pelo cliente
- **THEN** o backend ignora esse mecanismo e usa exclusivamente a identidade autenticada, ou rejeita a entrada inválida.

#### Scenario: Privacidade do formulário
- **WHEN** a tela de alteração de senha é enviada ou cancelada
- **THEN** os campos são mascarados, não são persistidos no estado durável do frontend nem enviados a logs/auditoria, e são limpos ao fim da ação.

#### Scenario: Sessões emitidas anteriormente
- **WHEN** a senha é alterada com sucesso
- **THEN** o sistema encerra a sessão local atual, mas não afirma que tokens emitidos em outros dispositivos foram revogados sem mecanismo e validação remotos específicos.

#### Scenario: Habilitação da funcionalidade
- **WHEN** a flag de alteração de senha está ausente ou desligada fora de uma execução local explícita
- **THEN** o fluxo de alteração permanece indisponível e nenhum PATCH de senha é enviado
- **AND** ativação permanente depende de revisão operacional e de segurança separada.
