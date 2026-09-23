import reflex as rx


class LoginState(rx.State):
    email: str = ""
    password: str = ""

    def set_email(self, value: str):
        self.email = value

    def set_password(self, value: str):
        self.password = value


def login() -> rx.Component:
    return rx.center(
        rx.box(
            rx.vstack(
                rx.heading("Sistema de Gerenciamento de Estoque", size="7"),
                rx.text("Acesso ao sistema", color="#666"),
                rx.divider(),
                rx.vstack(
                    rx.text("E-mail", weight="bold"),
                    rx.input(
                        placeholder="usuario@empresa.com",
                        value=LoginState.email,
                        on_change=LoginState.set_email,
                        width="100%",
                    ),
                    rx.text("Senha", weight="bold"),
                    rx.input(
                        placeholder="••••••••",
                        type="password",
                        value=LoginState.password,
                        on_change=LoginState.set_password,
                        width="100%",
                    ),
                    rx.link(
                        rx.button("Entrar", width="100%"),
                        href="/dashboard",
                        width="100%",
                    ),
                    rx.text(
                        "Protótipo: autenticação totalmente mockada.",
                        size="2",
                        color="#777",
                    ),
                    width="100%",
                    align="stretch",
                    spacing="3",
                ),
                width="100%",
                align="stretch",
                spacing="4",
            ),
            width="420px",
            max_width="90vw",
            padding="2rem",
            border="1px solid #ddd",
            border_radius="0.6rem",
        ),
        min_height="100vh",
        padding="2rem",
    )
