"""Administração de usuários do estoque."""

import logging
import re
from typing import Any

import reflex as rx

from ..components.layout import page, section
from ..services.xano_client import (
    XanoAuthError,
    XanoError,
    XanoPermissionError,
    XanoRequestError,
    auth_client,
)
from ..state import AuthState


logger = logging.getLogger(__name__)
USER_GRID = "60px minmax(180px, 1.2fr) minmax(220px, 1.5fr) minmax(180px, 1fr) 100px 100px"


class UserState(rx.State):
    users: list[dict[str, str]] = []
    profiles: list[dict[str, str]] = []
    is_loading: bool = False
    profiles_loading: bool = False
    error_message: str = ""
    profile_error: str = ""
    success_message: str = ""
    search_term: str = ""
    applied_search_term: str = ""
    current_page: int = 1
    per_page: int = 20
    total_items: int = 0
    total_pages: int = 1
    next_page: int | None = None
    prev_page: int | None = None

    modal_open: bool = False
    editing_user_id: str = ""
    loading_user_id: str = ""
    form_name: str = ""
    form_email: str = ""
    form_profile_id: str = ""
    form_error: str = ""
    is_saving: bool = False
    is_self_edit: bool = False
    editing_is_active: bool = True
    status_confirmation_open: bool = False
    status_loading: bool = False
    status_error: str = ""
    show_create_password: bool = False
    reset_modal_open: bool = False
    reset_loading: bool = False
    reset_error: str = ""
    show_reset_password: bool = False
    show_reset_password_confirm: bool = False

    @rx.var
    def has_profiles(self) -> bool:
        return bool(self.profiles)

    @rx.var
    def has_users(self) -> bool:
        return bool(self.users)

    def load_page(self):
        return [AuthState.require_auth(), UserState.load_users(1), UserState.load_profiles()]

    async def _session(self) -> tuple[str, int | None, int]:
        auth_state = await self.get_state(AuthState)
        token = str(auth_state.auth_token or "").strip()
        if not token or not auth_state.session_is_valid or not auth_state.is_administrator:
            return "", None, 0
        return str(auth_state.auth_token or "").strip(), auth_state.inventory_profile_id, auth_state.user_id

    @staticmethod
    def _user_item(item: dict[str, Any]) -> dict[str, str]:
        return {
            "id": str(item.get("id") or ""),
            "name": str(item.get("name") or ""),
            "email": str(item.get("email") or ""),
            "inventory_profile_id": str(item.get("inventory_profile_id") or ""),
            "profile_name": str(item.get("profile_name") or "Sem perfil atribuído"),
            "is_active": "false" if item.get("is_active") is False else "true",
        }

    async def _fetch_page(self, token: str, page_number: int) -> None:
        response = await auth_client.list_users(
            token, page=page_number, per_page=self.per_page,
            search=self.applied_search_term or None,
        )
        self.users = [
            self._user_item(item)
            for item in response["items"]
            if isinstance(item, dict) and item.get("id") is not None
        ]
        self.current_page = int(response.get("curPage") or page_number)
        self.total_items = int(response.get("itemsTotal") or 0)
        self.total_pages = max(1, int(response.get("pageTotal") or 0))
        self.next_page = int(response["nextPage"]) if response.get("nextPage") is not None else None
        self.prev_page = int(response["prevPage"]) if response.get("prevPage") is not None else None

    async def load_users(self, page_number: int = 1):
        self.is_loading = True
        self.error_message = ""
        self.users = []
        yield
        token, profile_id, _ = await self._session()
        if not token:
            self.is_loading = False
            yield rx.redirect("/")
            return
        if profile_id != 1:
            self.is_loading = False
            yield rx.redirect("/dashboard")
            return
        try:
            await self._fetch_page(token, page_number)
        except XanoAuthError:
            yield rx.redirect("/")
            return
        except XanoPermissionError:
            self.error_message = "Você não possui permissão para consultar usuários."
        except XanoError:
            self.error_message = "Não foi possível carregar os usuários. Tente novamente."
        except Exception:
            logger.exception("User list failed")
            self.error_message = "Não foi possível carregar os usuários. Tente novamente."
        finally:
            self.is_loading = False

    async def load_profiles(self):
        token, profile_id, _ = await self._session()
        if not token or profile_id != 1:
            return
        self.profiles_loading = True
        self.profile_error = ""
        try:
            response = await auth_client.get_inventory_profiles(token)
            self.profiles = [
                {
                    "id": str(item["id"]),
                    "code": str(item.get("code") or ""),
                    "name": str(item.get("display_name") or item.get("code") or ""),
                }
                for item in response["profiles"]
                if isinstance(item, dict) and item.get("id") is not None
            ]
        except XanoError:
            self.profiles = []
            self.profile_error = "Não foi possível carregar os perfis."
        except Exception:
            logger.exception("User profile options failed")
            self.profiles = []
            self.profile_error = "Não foi possível carregar os perfis."
        finally:
            self.profiles_loading = False

    def change_search(self, value: str):
        self.search_term = value

    def search_users(self):
        self.applied_search_term = self.search_term.strip()
        self.current_page = 1
        return UserState.load_users(1)

    def previous_page(self):
        if self.prev_page is not None:
            return UserState.load_users(self.prev_page)

    def following_page(self):
        if self.next_page is not None:
            return UserState.load_users(self.next_page)

    def _clear_form(self):
        self.editing_user_id = ""
        self.form_name = ""
        self.form_email = ""
        self.form_profile_id = ""
        self.form_error = ""
        self.is_self_edit = False
        self.editing_is_active = True
        self.show_create_password = False

    def open_create_modal(self):
        if not self.profiles:
            self.profile_error = "Não foi possível carregar os perfis."
            return
        self._clear_form()
        self.success_message = ""
        self.modal_open = True

    def close_modal(self):
        if self.is_saving:
            return
        self.modal_open = False
        self._clear_form()

    def toggle_create_password(self):
        self.show_create_password = not self.show_create_password

    def open_reset_modal(self):
        if not self.editing_user_id or self.is_saving:
            return
        self.reset_error = ""
        self.show_reset_password = False
        self.show_reset_password_confirm = False
        self.modal_open = False
        self.reset_modal_open = True

    def close_reset_modal(self):
        if self.reset_loading:
            return
        self.reset_modal_open = False
        self.reset_error = ""
        self.modal_open = True

    def toggle_reset_password(self):
        self.show_reset_password = not self.show_reset_password

    def toggle_reset_password_confirm(self):
        self.show_reset_password_confirm = not self.show_reset_password_confirm

    async def begin_edit(self, user_id: str):
        if self.loading_user_id or self.is_saving:
            return
        token, profile_id, own_user_id = await self._session()
        if not token or profile_id != 1:
            yield rx.redirect("/dashboard" if token else "/")
            return
        self.loading_user_id = user_id
        self.error_message = ""
        yield
        try:
            item = await auth_client.get_user(token, int(user_id))
            self._clear_form()
            self.editing_user_id = str(item["id"])
            self.form_name = str(item.get("name") or "")
            self.form_email = str(item.get("email") or "")
            self.form_profile_id = str(item.get("inventory_profile_id") or "")
            self.is_self_edit = int(item["id"]) == own_user_id
            self.editing_is_active = item.get("is_active") is not False
            self.modal_open = True
        except XanoAuthError:
            yield rx.redirect("/")
            return
        except XanoRequestError as exc:
            self.error_message = (
                "Usuário não encontrado. Atualize a listagem."
                if exc.error_code == "USER_NOT_FOUND"
                else "Não foi possível carregar o usuário."
            )
        except XanoError:
            self.error_message = "Não foi possível carregar o usuário."
        except Exception:
            logger.exception("User detail failed")
            self.error_message = "Não foi possível carregar o usuário."
        finally:
            self.loading_user_id = ""

    def change_name(self, value: str):
        self.form_name = value

    def change_email(self, value: str):
        self.form_email = value

    def change_profile(self, value: str):
        if not self.is_self_edit:
            self.form_profile_id = value

    def open_status_confirmation(self):
        if not self.editing_user_id or self.is_saving or self.status_loading:
            return
        if self.is_self_edit and self.editing_is_active:
            self.form_error = "Você não pode inativar seu próprio usuário."
            return
        self.status_error = ""
        self.modal_open = False
        self.status_confirmation_open = True

    def close_status_confirmation(self):
        if self.status_loading:
            return
        self.status_confirmation_open = False
        self.status_error = ""
        self.modal_open = True

    async def confirm_status_change(self):
        if self.status_loading or not self.editing_user_id:
            return
        self.status_error = ""
        token, profile_id, own_user_id = await self._session()
        if not token or profile_id != 1:
            yield rx.redirect("/dashboard" if token else "/")
            return
        if self.editing_is_active and int(self.editing_user_id) == own_user_id:
            self.status_error = "Você não pode inativar seu próprio usuário."
            return
        self.status_loading = True
        yield
        try:
            if self.editing_is_active:
                await auth_client.inactivate_user(token, int(self.editing_user_id))
                message = "Usuário inativado com sucesso."
            else:
                await auth_client.activate_user(token, int(self.editing_user_id))
                message = "Usuário ativado com sucesso."
            self.status_confirmation_open = False
            self._clear_form()
            self.success_message = message
            try:
                await self._fetch_page(token, self.current_page)
            except XanoError:
                self.error_message = "Status alterado, mas não foi possível atualizar a listagem."
        except XanoAuthError:
            yield rx.redirect("/")
        except XanoPermissionError as exc:
            self.status_error = (
                "Você não pode inativar seu próprio usuário."
                if "SELF_INACTIVATION_FORBIDDEN" in str(exc.payload)
                else "Não é possível inativar o último Líder ativo."
                if "LAST_LEADER_REQUIRED" in str(exc.payload)
                else "Você não possui permissão para alterar o status."
            )
        except XanoRequestError as exc:
            self.status_error = "Usuário não encontrado." if exc.error_code == "USER_NOT_FOUND" else "Não foi possível alterar o status."
        except XanoError:
            self.status_error = "Não foi possível alterar o status."
        except Exception:
            logger.exception("User status change failed")
            self.status_error = "Não foi possível alterar o status."
        finally:
            self.status_loading = False

    @staticmethod
    def _save_error(exc: XanoRequestError) -> str:
        if exc.error_code in {"DUPLICATE_EMAIL", "DUPLICATE_VALUE"}:
            return "Já existe um usuário cadastrado com este e-mail."
        if exc.error_code == "PASSWORD_MISMATCH":
            return "A confirmação da senha não confere."
        if exc.error_code in {"PROFILE_INVALID", "IMMUTABLE_PROFILE"}:
            return "O perfil selecionado não pode ser atribuído a este usuário."
        if exc.error_code == "USER_NOT_FOUND":
            return "Usuário não encontrado. Atualize a listagem."
        if exc.error_code in {"INVALID_INPUT", "INPUT_ERROR", "INPUTERROR", "VALIDATION_ERROR"}:
            return "Confira o nome, e-mail, perfil e requisitos da senha."
        return "Não foi possível salvar o usuário."

    async def save_user(self, form_data: dict[str, Any]):
        if self.is_saving:
            return
        name = self.form_name.strip()
        email = self.form_email.strip().lower()
        profile_id = self.form_profile_id
        password = str(form_data.get("password") or "")
        editing_id = self.editing_user_id
        self.form_error = ""
        if not name:
            self.form_error = "Informe o nome do usuário."
            return
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            self.form_error = "Informe um e-mail válido."
            return
        if not profile_id.isdigit() or profile_id not in {item["id"] for item in self.profiles}:
            self.form_error = "Selecione um perfil."
            return
        if not editing_id and not password:
            self.form_error = "Informe uma senha."
            return
        if not editing_id and password and (
            len(password) < 8
            or not any(char.isascii() and char.isalpha() for char in password)
            or not any(char.isascii() and char.isdigit() for char in password)
        ):
            self.form_error = "A senha deve ter ao menos 8 caracteres, uma letra e um número."
            return

        token, current_profile, _ = await self._session()
        if not token or current_profile != 1:
            yield rx.redirect("/dashboard" if token else "/")
            return

        self.is_saving = True
        self.success_message = ""
        yield
        try:
            if editing_id:
                await auth_client.update_user(
                    token, int(editing_id), name=name, email=email,
                    inventory_profile_id=int(profile_id),
                )
                success = "Usuário atualizado com sucesso."
            else:
                await auth_client.create_user(
                    token, name=name, email=email, password=password,
                    confirm_password=password, inventory_profile_id=int(profile_id),
                )
                self.search_term = ""
                self.applied_search_term = ""
                self.current_page = 1
                success = "Usuário cadastrado com sucesso."
            self.modal_open = False
            self._clear_form()
            self.success_message = success
            try:
                await self._fetch_page(token, self.current_page)
            except XanoError:
                self.error_message = "Usuário salvo, mas não foi possível atualizar a listagem."
        except XanoAuthError:
            yield rx.redirect("/")
            return
        except XanoPermissionError:
            self.form_error = "Você não possui permissão para alterar usuários."
        except XanoRequestError as exc:
            self.form_error = self._save_error(exc)
        except XanoError:
            self.form_error = "Não foi possível salvar o usuário."
        except Exception:
            logger.exception("User save failed")
            self.form_error = "Não foi possível salvar o usuário."
        finally:
            self.is_saving = False

    async def submit_reset_password(self, form_data: dict[str, Any]):
        if self.reset_loading or not self.editing_user_id:
            return
        password = str(form_data.get("password") or "")
        confirmation = str(form_data.get("confirm_password") or "")
        self.reset_error = ""
        if not password:
            self.reset_error = "Informe a nova senha inicial."
            return
        if password != confirmation:
            self.reset_error = "A confirmação da senha não confere."
            return
        if len(password) < 8 or not any(c.isascii() and c.isalpha() for c in password) or not any(c.isascii() and c.isdigit() for c in password):
            self.reset_error = "A senha deve ter ao menos 8 caracteres, uma letra e um número."
            return
        token, profile_id, _ = await self._session()
        if not token or profile_id != 1:
            yield rx.redirect("/dashboard" if token else "/")
            return
        self.reset_loading = True
        yield
        try:
            await auth_client.reset_user_password(token, int(self.editing_user_id), password, confirmation)
            self.reset_modal_open = False
            self._clear_form()
            self.success_message = "Senha temporária definida. O usuário deverá alterá-la no próximo acesso."
        except XanoAuthError:
            yield rx.redirect("/")
            return
        except XanoPermissionError:
            self.reset_error = "Você não possui permissão para resetar senhas."
        except XanoRequestError as exc:
            self.reset_error = self._save_error(exc)
        except XanoError:
            self.reset_error = "Não foi possível resetar a senha."
        except Exception:
            logger.exception("User password reset failed")
            self.reset_error = "Não foi possível resetar a senha."
        finally:
            self.reset_loading = False


def _user_row(item: dict[str, str]) -> rx.Component:
    return rx.grid(
        rx.text(item["id"]),
        rx.text(item["name"]),
        rx.text(item["email"]),
        rx.text(item["profile_name"]),
        rx.cond(
            item["is_active"] == "true",
            rx.badge("Ativo", color_scheme="green"),
            rx.badge("Inativo", color_scheme="gray"),
        ),
        rx.button(
            rx.cond(UserState.loading_user_id == item["id"], rx.spinner(), "Editar"),
            on_click=UserState.begin_edit(item["id"]),
            disabled=UserState.loading_user_id != "",
            variant="soft",
            width="90px",
        ),
        columns="6", width="100%", column_gap="8px",
        style={"grid_template_columns": USER_GRID, "align_items": "center"},
        padding="0.75rem", border_bottom="1px solid #e5e7eb",
    )


def _users_table() -> rx.Component:
    headers = ["ID", "Nome", "E-mail", "Perfil", "Status", "Ações"]
    return rx.box(
        rx.grid(
            *[rx.text(label, weight="bold") for label in headers],
            columns="6", width="100%", column_gap="8px",
            style={"grid_template_columns": USER_GRID, "align_items": "center"},
            padding="0.75rem", background="#f5f5f5", border_bottom="1px solid #ddd",
        ),
        rx.vstack(rx.foreach(UserState.users, _user_row), width="100%", spacing="0"),
        width="100%", overflow_x="auto", border="1px solid #ddd", border_radius="0.4rem",
    )


def _password_input(label: str, name: str, visible: Any, toggle: Any, disabled: Any) -> rx.Component:
    return rx.vstack(
        rx.text(label),
        rx.hstack(
            rx.input(name=name, type=rx.cond(visible, "text", "password"), auto_complete=False, disabled=disabled, width="100%"),
            rx.button(
                rx.cond(visible, rx.icon("eye_off"), rx.icon("eye")),
                type="button", variant="ghost", on_click=toggle, disabled=disabled,
                aria_label="Mostrar ou ocultar senha",
            ),
            width="100%", align="center",
        ),
        width="100%", align="stretch", spacing="1",
    )


def _user_modal() -> rx.Component:
    return rx.cond(
        UserState.modal_open,
        rx.box(
            rx.box(
                rx.form(
                    rx.vstack(
                        rx.hstack(
                            rx.heading(rx.cond(UserState.editing_user_id != "", "Editar usuário", "Novo usuário"), size="5"),
                            rx.spacer(),
                            rx.button("×", type="button", variant="ghost", on_click=UserState.close_modal, disabled=UserState.is_saving),
                            width="100%", align="center",
                        ),
                        rx.vstack(
                            rx.text("Nome"),
                            rx.input(value=UserState.form_name, on_change=UserState.change_name, disabled=UserState.is_saving, width="100%"),
                            width="100%", align="stretch", spacing="1",
                        ),
                        rx.vstack(
                            rx.text("E-mail"),
                            rx.input(value=UserState.form_email, on_change=UserState.change_email, type="email", disabled=UserState.is_saving, width="100%"),
                            width="100%", align="stretch", spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Perfil"),
                            rx.select.root(
                                rx.select.trigger(placeholder="Selecione um perfil"),
                                rx.select.content(
                                    rx.foreach(
                                        UserState.profiles,
                                        lambda profile: rx.select.item(profile["name"], value=profile["id"]),
                                    ),
                                ),
                                value=UserState.form_profile_id,
                                on_change=UserState.change_profile,
                                disabled=UserState.is_saving | UserState.is_self_edit,
                            ),
                            rx.cond(UserState.is_self_edit, rx.text("Seu próprio perfil não pode ser alterado.", size="1", color="#64748b")),
                            width="100%", align="stretch", spacing="1",
                        ),
                        rx.cond(
                            UserState.editing_user_id == "",
                            rx.vstack(
                                _password_input("Senha inicial", "password", UserState.show_create_password, UserState.toggle_create_password, UserState.is_saving),
                                width="100%", align="stretch", spacing="3",
                            ),
                        ),
                        rx.cond(UserState.form_error != "", rx.text(UserState.form_error, color="#b91c1c")),
                        rx.hstack(
                            rx.cond(
                                (UserState.editing_user_id != "") & ~UserState.is_self_edit,
                                rx.button(
                                    rx.cond(UserState.editing_is_active, "Inativar usuário", "Ativar usuário"),
                                    type="button", on_click=UserState.open_status_confirmation,
                                    variant="soft", color_scheme="orange", disabled=UserState.is_saving,
                                ),
                            ),
                            rx.cond(
                                UserState.editing_user_id != "",
                                rx.button("Resetar senha", type="button", on_click=UserState.open_reset_modal, variant="soft", color_scheme="orange", disabled=UserState.is_saving),
                            ),
                            rx.spacer(),
                            rx.button("Cancelar", type="button", on_click=UserState.close_modal, variant="soft", disabled=UserState.is_saving),
                            rx.button(rx.cond(UserState.is_saving, rx.spinner(), "Salvar"), type="submit", disabled=UserState.is_saving),
                            width="100%", justify="end", spacing="3",
                        ),
                        width="100%", align="stretch", spacing="3",
                    ),
                    on_submit=UserState.save_user,
                    width="100%",
                ),
                width="100%", max_width="34rem", padding="1.5rem", background="white",
                border_radius="0.75rem", box_shadow="0 20px 40px rgba(15, 23, 42, 0.2)",
            ),
            position="fixed", top="0", left="0", right="0", bottom="0",
            z_index="2000", display="flex", align_items="center", justify_content="center",
            padding="1rem", background="rgba(15, 23, 42, 0.45)",
        ),
    )


def _reset_password_modal() -> rx.Component:
    return rx.cond(
        UserState.reset_modal_open,
        rx.box(
            rx.box(
                rx.form(
                    rx.vstack(
                        rx.heading("Resetar senha", size="5"),
                        rx.text("Usuário: ", UserState.form_name),
                        rx.text("Esta ação substituirá a senha atual por uma senha temporária. O usuário deverá criar uma nova senha no próximo acesso.", size="2", color="#64748b"),
                        _password_input("Nova senha inicial", "password", UserState.show_reset_password, UserState.toggle_reset_password, UserState.reset_loading),
                        _password_input("Confirmar nova senha inicial", "confirm_password", UserState.show_reset_password_confirm, UserState.toggle_reset_password_confirm, UserState.reset_loading),
                        rx.cond(UserState.reset_error != "", rx.text(UserState.reset_error, color="#b91c1c")),
                        rx.hstack(
                            rx.spacer(),
                            rx.button("Cancelar", type="button", on_click=UserState.close_reset_modal, disabled=UserState.reset_loading, variant="soft"),
                            rx.button("Resetar senha", type="submit", disabled=UserState.reset_loading, loading=UserState.reset_loading),
                            width="100%", justify="end", spacing="3",
                        ),
                        width="100%", align="stretch", spacing="3",
                    ),
                    on_submit=UserState.submit_reset_password, width="100%",
                ),
                width="100%", max_width="34rem", padding="1.5rem", background="white",
                border_radius="0.75rem", box_shadow="0 20px 40px rgba(15, 23, 42, 0.2)",
            ),
            position="fixed", top="0", left="0", right="0", bottom="0",
            z_index="2000", display="flex", align_items="center", justify_content="center",
            padding="1rem", background="rgba(15, 23, 42, 0.45)",
        ),
    )


def _status_confirmation_modal() -> rx.Component:
    return rx.cond(
        UserState.status_confirmation_open,
        rx.box(
            rx.vstack(
                rx.heading(rx.cond(UserState.editing_is_active, "Inativar usuário", "Ativar usuário"), size="5"),
                rx.text("Usuário: ", UserState.form_name),
                rx.text(
                    rx.cond(
                        UserState.editing_is_active,
                        "Inativar este usuário impedirá novos acessos ao sistema. O histórico existente será preservado.",
                        "Ativar este usuário permitirá que ele acesse o sistema novamente.",
                    ),
                ),
                rx.cond(UserState.status_error != "", rx.text(UserState.status_error, color="#b91c1c")),
                rx.hstack(
                    rx.spacer(),
                    rx.button("Cancelar", on_click=UserState.close_status_confirmation, variant="soft", disabled=UserState.status_loading),
                    rx.button(
                        rx.cond(UserState.editing_is_active, "Inativar usuário", "Ativar usuário"),
                        on_click=UserState.confirm_status_change,
                        loading=UserState.status_loading, disabled=UserState.status_loading,
                    ),
                    width="100%", justify="end", spacing="3",
                ),
                width="100%", max_width="34rem", padding="1.5rem", background="white",
                border_radius="0.75rem", box_shadow="0 20px 40px rgba(15, 23, 42, 0.2)",
                align="stretch", spacing="4",
            ),
            position="fixed", top="0", left="0", right="0", bottom="0",
            z_index="2000", display="flex", align_items="center", justify_content="center",
            padding="1rem", background="rgba(15, 23, 42, 0.45)",
        ),
    )


def usuarios() -> rx.Component:
    return page(
        "Usuários",
        rx.vstack(
            rx.hstack(
                rx.input(
                    value=UserState.search_term, on_change=UserState.change_search,
                    placeholder="Buscar por nome ou e-mail...", width="min(24rem, 100%)",
                ),
                rx.button("Buscar", on_click=UserState.search_users),
                rx.spacer(),
                rx.button("Novo usuário", on_click=UserState.open_create_modal, disabled=UserState.profiles_loading | ~UserState.has_profiles),
                width="100%", wrap="wrap", align="center", spacing="3",
            ),
            rx.cond(UserState.success_message != "", rx.text(UserState.success_message, color="#15803d")),
            rx.cond(UserState.error_message != "", rx.text(UserState.error_message, color="#b91c1c")),
            rx.cond(UserState.profile_error != "", rx.text(UserState.profile_error, color="#b91c1c")),
            section(
                "Usuários cadastrados",
                rx.cond(
                    UserState.is_loading,
                    rx.center(rx.spinner(), rx.text("Carregando usuários..."), width="100%", padding="2rem"),
                    rx.cond(
                        UserState.error_message != "",
                        rx.fragment(),
                        rx.cond(UserState.has_users, _users_table(), rx.text("Nenhum usuário encontrado.")),
                    ),
                ),
            ),
            rx.hstack(
                rx.button("Anterior", on_click=UserState.previous_page, disabled=UserState.is_loading | (UserState.prev_page == None), variant="soft"),
                rx.spacer(),
                rx.text("Página ", UserState.current_page, " de ", UserState.total_pages, " · ", UserState.total_items, " usuários"),
                rx.spacer(),
                rx.button("Próxima", on_click=UserState.following_page, disabled=UserState.is_loading | (UserState.next_page == None), variant="soft"),
                width="100%", align="center",
            ),
            _user_modal(),
            _reset_password_modal(),
            _status_confirmation_modal(),
            width="100%", align="stretch", spacing="4",
        ),
    )
