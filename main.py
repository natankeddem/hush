import mylogging
import logging

logger = logging.getLogger(__name__)
import os

if not os.path.exists("data"):
    logger.warning("Could not find 'data' directory, verify bind mounts.")
    if os.path.exists(".nicegui"):
        logger.warning("Creating 'data' directory symlink.")
        os.symlink(".nicegui", "data", target_is_directory=True)
    else:
        logger.warning("Creating 'data' directory, settings will not be persistent.")
        os.makedirs("data")
else:
    logger.warning("Found 'data' directory.")
os.environ.setdefault("NICEGUI_STORAGE_PATH", "data")


if __name__ in {"__main__", "__mp_main__"}:
    from nicegui import app, ui  # type: ignore

    ui.card.default_style("max-width: none")
    ui.card.default_props("flat bordered")
    ui.input.default_props("outlined dense hide-bottom-space")
    ui.number.default_props("outlined dense hide-bottom-space")
    ui.button.default_props("outline dense")
    ui.select.default_props("outlined dense dense-options")
    ui.checkbox.default_props("dense")
    ui.stepper.default_props("flat")
    ui.stepper.default_classes("full-size-stepper")

    from hush import page, logo, control
    from hush.hardware.factory import Factory

    launcher = control.Launcher()
    launcher_timer = ui.timer(1, launcher.run)

    async def on_shutdown() -> None:
        logger.info("Shutdown launcher...")
        launcher_timer.cancel()
        await launcher.wait_on_not_busy()
        logger.info("Closing drivers...")
        await Factory.close_all()

    app.on_startup(lambda: print(f"Starting hush, bound to the following addresses {', '.join(app.urls)}.", flush=True))
    app.on_shutdown(on_shutdown)
    page.build()
    ui.run(title="hush", favicon="🙊", dark=True, reload=False, show=False, show_welcome_message=False)
