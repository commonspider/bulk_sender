from bulk_sender import create_app, driver_init

driver_init(
    user_data_dir="profile",
    headless=False,
    implicit_wait=5,
)
app = create_app()
app.run()
