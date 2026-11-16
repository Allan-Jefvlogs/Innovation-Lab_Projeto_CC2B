import reflex as rx

config = rx.Config(
    app_name="Meu_projeto",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="light",
                accent_color="jade",
                gray_color="sage",
                panel_background="solid",
                radius="medium",
            ),
        ),
    ]
)
