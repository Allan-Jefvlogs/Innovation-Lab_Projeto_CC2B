"""Consulta e edição administrativa dos grants de perfis do estoque."""

import logging
from typing import Any, TypedDict

import reflex as rx

from ..components.layout import page, section
from ..services.xano_client import (
    XanoAuthError,
    XanoError,
    XanoPermissionError,
    XanoRequestError,
    XanoServerError,
    auth_client,
)
from ..state import AuthState


logger = logging.getLogger(__name__)

MODULE_NAMES = {
    "category": "Categorias",
    "product": "Produtos",
    "supplier": "Fornecedores",
    "stock": "Estoque",
    "movement": "Histórico",
    "report": "Relatórios",
}
ACTION_NAMES = {
    "read": "Visualizar",
    "create": "Criar",
    "update": "Editar",
    "inactivate": "Inativar",
    "entry": "Registrar entrada",
    "exit": "Registrar saída",
}
MODULE_ORDER = ("category", "product", "supplier", "stock", "movement", "report")


class PermissionItem(TypedDict):
    code: str
    label: str
    selected: bool


class PermissionGroup(TypedDict):
    name: str
    permissions: list[PermissionItem]


def _permission_label(code: str, resource: str, action: str) -> str:
    if action in {"entry", "exit"}:
        return ACTION_NAMES[action]
    noun = {
        "category": "categorias",
        "product": "produtos",
        "supplier": "fornecedores",
        "stock": "estoque",
        "movement": "histórico",
        "report": "relatórios",
    }.get(resource)
    verb = ACTION_NAMES.get(action)
    return f"{verb} {noun}" if verb and noun else code


class PermissionState(rx.State):
    profiles: list[dict[str, str]] = []
    catalog: list[dict[str, str]] = []
    profile_grants: dict[str, list[str]] = {}
    profile_revisions: dict[str, int] = {}
    selected_profile_code: str = ""
    saved_codes: list[str] = []
    draft_codes: list[str] = []
    is_loading: bool = True
    is_saving: bool = False
    error_message: str = ""
    success_message: str = ""
    info_message: str = ""

    @rx.var
    def can_edit(self) -> bool:
        return self.selected_profile_code in {"stockkeeper", "read_only"}

    @rx.var
    def is_dirty(self) -> bool:
        return set(self.saved_codes) != set(self.draft_codes)

    @rx.var
    def has_catalog(self) -> bool:
        return bool(self.catalog)

    @rx.var
    def selected_profile_name(self) -> str:
        for profile in self.profiles:
            if profile["code"] == self.selected_profile_code:
                return profile["name"]
        return ""

    @rx.var
    def permission_groups(self) -> list[PermissionGroup]:
        by_resource: dict[str, list[PermissionItem]] = {}
        selected = set(self.draft_codes)
        for item in self.catalog:
            resource = item["resource"]
            by_resource.setdefault(resource, []).append(
                {
                    "code": item["code"],
                    "label": _permission_label(item["code"], resource, item["action"]),
                    "selected": item["code"] in selected,
                }
            )
        ordered_resources = [name for name in MODULE_ORDER if name in by_resource]
        ordered_resources.extend(sorted(name for name in by_resource if name not in MODULE_ORDER))
        return [
            {"name": MODULE_NAMES.get(resource, resource.replace("_", " ").title()), "permissions": by_resource[resource]}
            for resource in ordered_resources
        ]

    def load_page(self):
        return [AuthState.require_auth(), PermissionState.load_permissions()]

    async def _session(self) -> tuple[str, int | None]:
        auth_state = await self.get_state(AuthState)
        token = str(auth_state.auth_token or "").strip()
        if not token or not auth_state.session_is_valid or not auth_state.is_administrator:
            return "", None
        return str(auth_state.auth_token or "").strip(), auth_state.inventory_profile_id

    def _use_profile(self, code: str) -> None:
        self.selected_profile_code = code
        codes = self.profile_grants.get(code, [])
        self.saved_codes = list(codes)
        self.draft_codes = list(codes)

    def _ingest(self, response: dict[str, Any], preferred_code: str = "") -> None:
        raw_profiles = response.get("profiles")
        raw_catalog = response.get("permissions")
        raw_matrix = response.get("permission_matrix")
        if not all(isinstance(value, list) for value in (raw_profiles, raw_catalog, raw_matrix)):
            raise XanoServerError("A matriz de permissões retornou um formato inesperado.")

        profiles = [
            {"code": str(item["code"]), "name": str(item["display_name"])}
            for item in raw_profiles
            if isinstance(item, dict) and item.get("code") and item.get("display_name")
        ]
        catalog = [
            {"code": str(item["code"]), "resource": str(item["resource"]), "action": str(item["action"])}
            for item in raw_catalog
            if isinstance(item, dict) and item.get("code") and item.get("resource") and item.get("action")
        ]
        if len(profiles) != len(raw_profiles) or len(catalog) != len(raw_catalog):
            raise XanoServerError("O catálogo de permissões retornou dados incompletos.")
        catalog_codes = {item["code"] for item in catalog}
        if len(catalog_codes) != len(catalog):
            raise XanoServerError("O catálogo de permissões contém códigos duplicados.")

        grants: dict[str, list[str]] = {}
        revisions: dict[str, int] = {}
        for item in raw_matrix:
            if not isinstance(item, dict) or not item.get("profile_code"):
                raise XanoServerError("A matriz de permissões retornou um perfil inválido.")
            code = str(item["profile_code"])
            if code == "administrator":
                grants[code] = [entry["code"] for entry in catalog]
                continue
            raw_codes = item.get("permissions")
            if not isinstance(raw_codes, list) or not all(isinstance(value, str) and value in catalog_codes for value in raw_codes):
                raise XanoServerError("A matriz de permissões retornou grants inválidos.")
            try:
                revision = int(item["permission_revision"])
            except (KeyError, TypeError, ValueError) as exc:
                raise XanoServerError("A matriz de permissões não informou a revisão do perfil.") from exc
            if revision < 1:
                raise XanoServerError("A revisão do perfil é inválida.")
            grants[code] = list(raw_codes)
            revisions[code] = revision

        if any(profile["code"] not in grants for profile in profiles):
            raise XanoServerError("A matriz de permissões não incluiu todos os perfis.")
        self.profiles = profiles
        self.catalog = catalog
        self.profile_grants = grants
        self.profile_revisions = revisions
        available_codes = {profile["code"] for profile in profiles}
        selected = preferred_code if preferred_code in available_codes else (profiles[0]["code"] if profiles else "")
        self._use_profile(selected)

    async def load_permissions(self):
        self.is_loading = True
        self.error_message = ""
        self.success_message = ""
        self.info_message = ""
        yield
        token, profile_id = await self._session()
        if not token:
            self.is_loading = False
            yield rx.redirect("/")
            return
        if profile_id != 1:
            self.is_loading = False
            yield rx.redirect("/dashboard")
            return
        try:
            self._ingest(await auth_client.get_permissions(token), self.selected_profile_code)
        except XanoAuthError:
            yield rx.redirect("/")
        except XanoPermissionError:
            self.error_message = "Você não possui permissão para consultar perfis e permissões."
        except XanoError:
            self.error_message = "Não foi possível carregar perfis e permissões. Tente novamente."
        except Exception:
            logger.exception("Permission matrix load failed")
            self.error_message = "Não foi possível carregar perfis e permissões. Tente novamente."
        finally:
            self.is_loading = False

    def select_profile(self, code: str):
        if self.is_saving or code not in {profile["code"] for profile in self.profiles}:
            return
        self.info_message = "Alterações não salvas foram descartadas." if self.is_dirty else ""
        self.error_message = ""
        self.success_message = ""
        self._use_profile(code)

    def toggle_permission(self, code: str, checked: bool):
        if not self.can_edit or self.is_saving or code not in {item["code"] for item in self.catalog}:
            return
        selected = set(self.draft_codes)
        if checked:
            selected.add(code)
        else:
            selected.discard(code)
        self.draft_codes = [item["code"] for item in self.catalog if item["code"] in selected]
        self.error_message = ""
        self.success_message = ""

    def cancel_changes(self):
        if self.is_saving:
            return
        self.draft_codes = list(self.saved_codes)
        self.info_message = "Alterações não salvas foram descartadas."
        self.error_message = ""

    async def save_permissions(self):
        code = self.selected_profile_code
        if self.is_saving or not self.can_edit or not self.is_dirty:
            return
        revision = self.profile_revisions.get(code)
        if revision is None:
            self.error_message = "Não foi possível identificar a revisão do perfil. Recarregue a página."
            return
        token, profile_id = await self._session()
        if not token or profile_id != 1:
            yield rx.redirect("/dashboard" if token else "/")
            return
        self.is_saving = True
        self.error_message = ""
        self.success_message = ""
        self.info_message = ""
        yield
        try:
            selected_codes = list(self.draft_codes)
            response = await auth_client.update_profile_permissions(token, code, selected_codes, revision)
            if response.get("profile_code") != code or not isinstance(response.get("permissions"), list):
                raise XanoServerError("O Xano retornou um salvamento em formato inesperado.")
            new_revision = int(response["permission_revision"])
            self.profile_grants = {**self.profile_grants, code: list(response["permissions"])}
            self.profile_revisions = {**self.profile_revisions, code: new_revision}
            self.saved_codes = list(response["permissions"])
            self.draft_codes = list(response["permissions"])
            self.success_message = "Permissões atualizadas com sucesso."
            try:
                self._ingest(await auth_client.get_permissions(token), code)
            except XanoError:
                self.info_message = "Permissões salvas; não foi possível confirmar a matriz atualizada."
        except XanoAuthError:
            yield rx.redirect("/")
        except XanoPermissionError:
            self.error_message = "Você não possui permissão para alterar os grants deste perfil."
        except XanoRequestError as exc:
            if exc.error_code == "PERMISSION_REVISION_CONFLICT":
                try:
                    self._ingest(await auth_client.get_permissions(token), code)
                    self.error_message = "As permissões mudaram em outra sessão. Revise os dados atualizados antes de salvar novamente."
                except XanoError:
                    self.error_message = "As permissões mudaram em outra sessão. Recarregue a página antes de salvar."
            else:
                self.error_message = "Não foi possível atualizar as permissões. Confira a seleção e tente novamente."
        except XanoError:
            self.error_message = "Não foi possível atualizar as permissões. Tente novamente."
        except Exception:
            logger.exception("Permission grant update failed")
            self.error_message = "Não foi possível atualizar as permissões. Tente novamente."
        finally:
            self.is_saving = False


def _permission_row(item: PermissionItem) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            item["label"], checked=item["selected"],
            on_change=lambda checked: PermissionState.toggle_permission(item["code"], checked),
            disabled=~PermissionState.can_edit | PermissionState.is_saving,
        ),
        rx.spacer(),
        rx.text(item["code"], size="1", color="#64748b"),
        width="100%", align="center", spacing="3",
    )


def _permission_group(group: PermissionGroup) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading(group["name"], size="4"),
            rx.foreach(group["permissions"], _permission_row),
            width="100%", align="stretch", spacing="3",
        ),
        border="1px solid #e5e7eb", border_radius="0.5rem", padding="1rem", width="100%",
    )


def perfis() -> rx.Component:
    return page(
        "Perfis e permissões",
        rx.vstack(
            rx.cond(PermissionState.error_message != "", rx.callout(PermissionState.error_message, icon="triangle_alert", color_scheme="ruby", width="100%")),
            rx.cond(PermissionState.success_message != "", rx.callout(PermissionState.success_message, icon="circle_check", color_scheme="green", width="100%")),
            rx.cond(PermissionState.info_message != "", rx.text(PermissionState.info_message, color="#64748b", size="2")),
            section(
                "Perfil selecionado",
                rx.vstack(
                    rx.select.root(
                        rx.select.trigger(placeholder="Selecione um perfil", width="100%"),
                        rx.select.content(
                            rx.foreach(
                                PermissionState.profiles,
                                lambda profile: rx.select.item(profile["name"], value=profile["code"]),
                            ),
                        ),
                        value=PermissionState.selected_profile_code,
                        on_change=PermissionState.select_profile,
                        disabled=PermissionState.is_loading | PermissionState.is_saving,
                    ),
                    rx.cond(
                        PermissionState.selected_profile_code == "administrator",
                        rx.text("O perfil Líder possui permissões administrativas protegidas.", color="#64748b", size="2"),
                    ),
                    width="100%", max_width="28rem", align="stretch", spacing="3",
                ),
            ),
            section(
                "Permissões",
                rx.cond(
                    PermissionState.is_loading,
                    rx.center(rx.spinner(), rx.text("Carregando permissões..."), padding="2rem", width="100%"),
                    rx.cond(
                        PermissionState.has_catalog,
                        rx.grid(
                            rx.foreach(PermissionState.permission_groups, _permission_group),
                            width="100%", gap="1rem",
                            style={"grid_template_columns": "repeat(auto-fit, minmax(260px, 1fr))"},
                        ),
                        rx.text("Nenhuma permissão disponível."),
                    ),
                ),
            ),
            rx.cond(
                PermissionState.can_edit,
                rx.hstack(
                    rx.cond(PermissionState.is_dirty, rx.text("Alterações não salvas", color="#b45309", size="2")),
                    rx.spacer(),
                    rx.button("Cancelar alterações", on_click=PermissionState.cancel_changes, disabled=~PermissionState.is_dirty | PermissionState.is_saving, variant="soft"),
                    rx.button("Salvar permissões", on_click=PermissionState.save_permissions, disabled=~PermissionState.is_dirty | PermissionState.is_saving, loading=PermissionState.is_saving),
                    width="100%", wrap="wrap", align="center", spacing="3",
                ),
            ),
            width="100%", align="stretch", spacing="4",
        ),
    )
