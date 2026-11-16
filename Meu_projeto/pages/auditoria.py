"""Consulta administrativa da trilha de auditoria persistida no Xano."""

from __future__ import annotations

import logging
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import reflex as rx

from ..components.layout import page, section
from ..components.theme import ERROR_TEXT, TABLE_HEADER, TEXT_MUTED
from ..services.audit_export import (
    AuditExportConsistencyError,
    AuditExportLimitError,
    collect_all_audit_logs,
)
from ..services.audit_format import present_event, referenced_profile_ids
from ..services.audit_pdf import build_audit_pdf
from ..services.xano_client import (
    XanoAuthError,
    XanoError,
    XanoPermissionError,
    auth_client,
)
from ..state import AuthState

logger = logging.getLogger(__name__)
PAGE_SIZE = 20
EXPORT_LIMIT = 500


def _date_epoch(value: str, *, end_of_day: bool = False) -> int | None:
    if not value:
        return None

    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
        local = datetime.combine(
            parsed,
            time.max if end_of_day else time.min,
        )
        return int(
            local.replace(
                tzinfo=ZoneInfo("America/Sao_Paulo")
            ).timestamp()
            * 1000
        )
    except (TypeError, ValueError):
        return None


class AuditState(rx.State):
    events: list[dict[str, str]] = []
    is_loading: bool = False
    error_message: str = ""
    access_denied: bool = False

    date_from: str = ""
    date_to: str = ""
    actor_user_id: str = ""
    action_filter: str = "Todas"
    entity_filter: str = "Todas"

    current_page: int = 1
    total_items: int = 0
    total_pages: int = 1
    is_exporting: bool = False
    export_message: str = ""
    profile_names: dict[int, str] = {}
    profile_names_loaded: bool = False

    def change_date_from(self, value: str):
        self.date_from = value

    def change_date_to(self, value: str):
        self.date_to = value

    def change_actor_user_id(self, value: str):
        self.actor_user_id = value

    def change_action_filter(self, value: str):
        self.action_filter = value

    def change_entity_filter(self, value: str):
        self.entity_filter = value

    async def load_page(self):
        async for event in self._load():
            yield event

    async def _load(self, *, reset_page: bool = False):
        if self.is_loading:
            return

        if reset_page:
            self.current_page = 1

        self.is_loading = True
        self.error_message = ""
        self.access_denied = False
        yield

        auth = await self.get_state(AuthState)
        redirect = await auth.require_auth()

        if redirect is not None:
            self.is_loading = False
            yield redirect
            return

        if not auth.session_is_valid:
            self.is_loading = False
            self.error_message = auth.session_status_message
            return

        if not auth.is_administrator:
            self.access_denied = True
            self.events = []
            self.is_loading = False
            return

        actor_id: int | None = None

        if self.actor_user_id.strip():
            try:
                actor_id = int(self.actor_user_id)

                if actor_id <= 0:
                    raise ValueError
            except ValueError:
                self.error_message = (
                    "Informe um ID de usuário positivo "
                    "ou deixe o filtro vazio."
                )
                self.is_loading = False
                return

        if (
            self.date_from
            and self.date_to
            and self.date_from > self.date_to
        ):
            self.error_message = (
                "A data inicial deve ser anterior ou igual "
                "à data final."
            )
            self.is_loading = False
            return

        action = (
            ""
            if self.action_filter == "Todas"
            else self.action_filter
        )
        entity = (
            ""
            if self.entity_filter == "Todas"
            else self.entity_filter
        )

        try:
            result = await auth_client.list_audit_logs(
                str(auth.auth_token or "").strip(),
                page=self.current_page,
                per_page=PAGE_SIZE,
                date_from=_date_epoch(self.date_from),
                date_to=_date_epoch(
                    self.date_to,
                    end_of_day=True,
                ),
                actor_user_id=actor_id,
                action_type=action,
                entity_type=entity,
            )

            await self._ensure_profile_names(
                str(auth.auth_token or "").strip(), result["items"]
            )
            self.events = [
                self._present(item, self.profile_names)
                for item in result["items"]
            ]
            self.total_items = result["itemsTotal"]
            self.total_pages = max(
                1,
                (self.total_items + PAGE_SIZE - 1) // PAGE_SIZE,
            )

            if self.current_page > self.total_pages:
                self.current_page = self.total_pages

        except XanoAuthError:
            self.events = []
            self.error_message = "Sua sessão expirou. Entre novamente."
            yield auth.logout()
            return

        except XanoPermissionError:
            self.events = []
            self.access_denied = True
            self.error_message = (
                "O Xano não autorizou a consulta de auditoria."
            )

        except XanoError as exc:
            logger.warning(
                "Audit read failed: status=%s exception_type=%s",
                exc.status_code,
                type(exc).__name__,
            )
            self.error_message = (
                "Não foi possível carregar a auditoria. "
                "Tente novamente."
            )

        except Exception as exc:
            logger.warning(
                "Audit read failed: exception_type=%s",
                type(exc).__name__,
            )
            self.error_message = (
                "Não foi possível carregar a auditoria. "
                "Tente novamente."
            )

        finally:
            self.is_loading = False

    async def _ensure_profile_names(
        self, token: str, items: list[dict[str, Any]]
    ) -> None:
        if self.profile_names_loaded or not referenced_profile_ids(items):
            return
        self.profile_names_loaded = True
        try:
            result = await auth_client.get_inventory_profiles(token)
            profiles = result.get("profiles", [])
            if isinstance(profiles, list):
                self.profile_names = {
                    int(profile["id"]): str(profile["display_name"])
                    for profile in profiles
                    if isinstance(profile, dict)
                    and isinstance(profile.get("id"), int)
                    and profile.get("id") > 0
                    and isinstance(profile.get("display_name"), str)
                    and profile.get("display_name").strip()
                }
        except XanoError as exc:
            logger.warning(
                "Audit profile label lookup unavailable: status=%s exception_type=%s",
                exc.status_code,
                type(exc).__name__,
            )

    @staticmethod
    def _present(
        item: dict[str, Any], profile_names: dict[int, str] | None = None
    ) -> dict[str, str]:
        return present_event(item, profile_names=profile_names)

    def _export_filters(self) -> dict[str, Any]:
        return {
            "date_from": _date_epoch(self.date_from),
            "date_to": _date_epoch(self.date_to, end_of_day=True),
            "actor_user_id": int(self.actor_user_id) if self.actor_user_id.strip() else None,
            "action_type": "" if self.action_filter == "Todas" else self.action_filter,
            "entity_type": "" if self.entity_filter == "Todas" else self.entity_filter,
        }

    def _filters_description(self) -> str:
        parts = []
        if self.date_from or self.date_to:
            parts.append(f"Período: {self.date_from or 'início'} a {self.date_to or 'hoje'}")
        if self.actor_user_id.strip():
            parts.append(f"ID do usuário: {self.actor_user_id.strip()}")
        if self.action_filter != "Todas":
            parts.append(f"Ação: {self.action_filter}")
        if self.entity_filter != "Todas":
            parts.append(f"Entidade: {self.entity_filter}")
        return "; ".join(parts) or "Todos os registros"

    async def export_pdf(self):
        if self.is_exporting or self.is_loading:
            return
        self.is_exporting = True
        self.export_message = ""
        self.error_message = ""
        yield
        auth = await self.get_state(AuthState)
        redirect = await auth.require_auth()
        if redirect is not None:
            self.is_exporting = False
            yield redirect
            return
        if not auth.session_is_valid:
            self.is_exporting = False
            self.export_message = auth.session_status_message
            return
        if not auth.is_administrator:
            self.access_denied = True
            self.is_exporting = False
            self.export_message = "A exportação está disponível somente para administradores."
            return
        if self.actor_user_id.strip():
            try:
                if int(self.actor_user_id) < 1:
                    raise ValueError
            except ValueError:
                self.is_exporting = False
                self.export_message = "Informe um ID de usuário positivo ou deixe o filtro vazio."
                return
        if self.date_from and self.date_to and self.date_from > self.date_to:
            self.is_exporting = False
            self.export_message = "A data inicial deve ser anterior ou igual à data final."
            return
        token = str(auth.auth_token or "").strip()
        filters = self._export_filters()
        filters_description = self._filters_description()

        async def fetch_page(**kwargs):
            return await auth_client.list_audit_logs(token, **kwargs)

        try:
            rows = await collect_all_audit_logs(
                fetch_page,
                filters=filters,
                max_records=EXPORT_LIMIT,
            )
            if not rows:
                self.export_message = "Não há registros para exportar com os filtros selecionados."
                return
            await self._ensure_profile_names(token, rows)
            formatted = [self._present(item, self.profile_names) for item in rows]
            emitted_at = datetime.now(ZoneInfo("America/Sao_Paulo"))
            content = build_audit_pdf(
                formatted,
                filters_description=filters_description,
                emitted_at=emitted_at,
            )
            filename = emitted_at.strftime("auditoria_nextstock_%Y-%m-%d.pdf")
            self.export_message = f"PDF gerado com {len(rows)} eventos."
            yield rx.download(data=content, filename=filename, mime_type="application/pdf")
        except AuditExportLimitError:
            self.export_message = (
                f"A exportação completa excede o limite de {EXPORT_LIMIT} eventos. "
                "Aplique filtros mais específicos; nenhum PDF parcial foi gerado."
            )
        except AuditExportConsistencyError:
            self.export_message = (
                "Os registros mudaram durante a exportação. Tente novamente; "
                "nenhum PDF parcial foi gerado."
            )
        except XanoAuthError:
            self.export_message = "Sua sessão expirou. Entre novamente."
            yield auth.logout()
            return
        except XanoPermissionError:
            self.access_denied = True
            self.export_message = "O Xano não autorizou a exportação da auditoria."
        except XanoError as exc:
            logger.warning(
                "Audit export failed: status=%s exception_type=%s",
                exc.status_code,
                type(exc).__name__,
            )
            self.export_message = "Não foi possível exportar a auditoria. Tente novamente."
        except Exception as exc:
            logger.warning(
                "Audit PDF generation failed: exception_type=%s",
                type(exc).__name__,
            )
            self.export_message = "Não foi possível gerar o PDF. Tente novamente."
        finally:
            self.is_exporting = False

    async def apply_filters(self):
        async for event in self._load(reset_page=True):
            yield event

    async def clear_filters(self):
        self.date_from = ""
        self.date_to = ""
        self.actor_user_id = ""
        self.action_filter = "Todas"
        self.entity_filter = "Todas"

        async for event in self._load(reset_page=True):
            yield event

    async def retry(self):
        async for event in self._load():
            yield event

    async def previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1

            async for event in self._load():
                yield event

    async def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1

            async for event in self._load():
                yield event


def _event_row(row: rx.Var[dict[str, str]]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(row["data"]),
        rx.table.cell(row["usuario"]),
        rx.table.cell(row["acao"]),
        rx.table.cell(row["entidade"]),
        rx.table.cell(row["registro"]),
        rx.table.cell(row["resumo"]),
        rx.table.cell(row["alteracoes"]),
    )


def auditoria() -> rx.Component:
    return page(
        "Auditoria",
        rx.vstack(
            rx.text(
                "Consulte ações registradas pelo Xano após "
                "a implantação da auditoria.",
                color=TEXT_MUTED,
            ),
            section(
                "Filtros",
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.text("De"),
                            rx.input(
                                type="date",
                                value=AuditState.date_from,
                                on_change=AuditState.change_date_from,
                            ),
                        ),
                        rx.vstack(
                            rx.text("Até"),
                            rx.input(
                                type="date",
                                value=AuditState.date_to,
                                on_change=AuditState.change_date_to,
                            ),
                        ),
                        rx.vstack(
                            rx.text("ID do usuário"),
                            rx.input(
                                value=AuditState.actor_user_id,
                                on_change=(
                                    AuditState.change_actor_user_id
                                ),
                                type="number",
                                min="1",
                            ),
                        ),
                        rx.vstack(
                            rx.text("Ação"),
                            rx.select(
                                [
                                    "Todas",
                                    "criado",
                                    "atualizado",
                                    "ativado",
                                    "inativado",
                                    "perfil_alterado",
                                    "permissoes_alteradas",
                                    "credencial_redefinida",
                                ],
                                value=AuditState.action_filter,
                                on_change=(
                                    AuditState.change_action_filter
                                ),
                            ),
                        ),
                        rx.vstack(
                            rx.text("Entidade"),
                            rx.select(
                                [
                                    "Todas",
                                    "produto",
                                    "categoria",
                                    "fornecedor",
                                    "usuario",
                                    "perfil",
                                ],
                                value=AuditState.entity_filter,
                                on_change=(
                                    AuditState.change_entity_filter
                                ),
                            ),
                        ),
                        wrap="wrap",
                        align="end",
                        spacing="3",
                    ),
                    rx.hstack(
                        rx.button(
                            "Aplicar filtros",
                            on_click=AuditState.apply_filters,
                        ),
                        rx.button(
                            "Limpar",
                            on_click=AuditState.clear_filters,
                            variant="soft",
                        ),
                        rx.button(
                            rx.cond(
                                AuditState.is_exporting,
                                rx.spinner(size="1"),
                                rx.icon("file-down", size=16),
                            ),
                            rx.cond(
                                AuditState.is_exporting,
                                "Gerando PDF...",
                                "Exportar PDF",
                            ),
                            on_click=AuditState.export_pdf,
                            disabled=(
                                AuditState.is_exporting
                                | AuditState.is_loading
                            ),
                            background="#8DBAA6",
                            color="#263B32",
                            _hover={"background": "#A6D0BA"},
                        ),
                    ),
                    rx.cond(
                        AuditState.export_message != "",
                        rx.text(
                            AuditState.export_message,
                            color=TEXT_MUTED,
                            role="status",
                            aria_live="polite",
                        ),
                        rx.fragment(),
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
                tone="mint",
            ),
            section(
                "Eventos registrados",
                rx.cond(
                    AuditState.access_denied,
                    rx.text(
                        "A consulta de auditoria está disponível "
                        "somente para administradores.",
                        role="status",
                    ),
                    rx.cond(
                        AuditState.is_loading,
                        rx.center(
                            rx.spinner(),
                            rx.text("Carregando auditoria..."),
                            width="100%",
                            padding="2rem",
                        ),
                        rx.cond(
                            AuditState.error_message != "",
                            rx.vstack(
                                rx.text(
                                    AuditState.error_message,
                                    color=ERROR_TEXT,
                                ),
                                rx.button(
                                    "Tentar novamente",
                                    on_click=AuditState.retry,
                                    size="1",
                                ),
                            ),
                            rx.cond(
                                AuditState.events.length() == 0,
                                rx.text(
                                    "Nenhum evento de auditoria "
                                    "registrado neste período.",
                                    color=TEXT_MUTED,
                                ),
                                rx.box(
                                    rx.table.root(
                                        rx.table.header(
                                            rx.table.row(
                                                *[
                                                    rx.table.column_header_cell(
                                                        label,
                                                        scope="col",
                                                    )
                                                    for label in [
                                                        "Data e hora",
                                                        "Usuário",
                                                        "Ação",
                                                        "Entidade",
                                                        "Registro",
                                                        "Resumo",
                                                        "Alterações",
                                                    ]
                                                ]
                                            ),
                                            background=TABLE_HEADER,
                                        ),
                                        rx.table.body(
                                            rx.foreach(
                                                AuditState.events,
                                                _event_row,
                                            )
                                        ),
                                        width="100%",
                                        variant="surface",
                                    ),
                                    width="100%",
                                    overflow_x="auto",
                                ),
                            ),
                        ),
                    ),
                ),
                tone="rose",
            ),
            rx.hstack(
                rx.button(
                    "Anterior",
                    on_click=AuditState.previous_page,
                    disabled=AuditState.current_page <= 1,
                    variant="soft",
                ),
                rx.text(
                    "Página ",
                    AuditState.current_page,
                    " de ",
                    AuditState.total_pages,
                    " · ",
                    AuditState.total_items,
                    " eventos",
                ),
                rx.button(
                    "Próxima",
                    on_click=AuditState.next_page,
                    disabled=(
                        AuditState.current_page
                        >= AuditState.total_pages
                    ),
                    variant="soft",
                ),
                width="100%",
                justify="between",
            ),
            width="100%",
            align="stretch",
            spacing="4",
        ),
    )
